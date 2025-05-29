import redis.asyncio as redis
import os
import json
from dotenv import load_dotenv
import logging
import traceback
from redis.asyncio.connection import ConnectionPool
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import backoff

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get Redis connection details from environment variables
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    logger.error("REDIS_URL environment variable is not set!")
    raise ValueError("REDIS_URL environment variable is required")

logger.info(f"Attempting to connect to Redis at {REDIS_URL.split('@')[-1]}")  # Log only the host part for security

# Create a connection pool
pool = ConnectionPool.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_timeout=10,
    socket_connect_timeout=10,
    retry_on_timeout=True,
    health_check_interval=30,
    max_connections=10,
    socket_keepalive=True
)

# Initialize Redis client with connection pool
try:
    redis_client = redis.Redis(connection_pool=pool)
    logger.info("Successfully initialized Redis client with connection pool")
except Exception as e:
    logger.error(f"Error connecting to Redis: {str(e)}\n{traceback.format_exc()}")
    raise

# Redis connection pool
redis_pool = None

def get_redis_url() -> str:
    """Get Redis URL from environment variable with validation."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL environment variable is not set")
    return redis_url

@backoff.on_exception(
    backoff.expo,
    (redis.ConnectionError, redis.TimeoutError),
    max_tries=3,
    max_time=30
)
async def get_redis_connection() -> redis.Redis:
    """Get a Redis connection from the pool with retry logic."""
    global redis_pool
    
    if redis_pool is None:
        try:
            redis_url = get_redis_url()
            redis_pool = redis.ConnectionPool.from_url(
                redis_url,
                decode_responses=True,
                max_connections=10,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            logger.info("Redis connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create Redis connection pool: {str(e)}\n{traceback.format_exc()}")
            raise
    
    try:
        client = redis.Redis(connection_pool=redis_pool)
        await client.ping()  # Test the connection
        return client
    except Exception as e:
        logger.error(f"Failed to get Redis connection: {str(e)}\n{traceback.format_exc()}")
        raise

async def close_redis_pool():
    """Close the Redis connection pool."""
    global redis_pool
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None
        logger.info("Redis connection pool closed")

class RedisError(Exception):
    """Custom exception for Redis operations."""
    pass

async def get_conversations() -> List[Dict[str, Any]]:
    """Get all conversations from Redis with improved error handling."""
    try:
        logger.info("Getting all conversation keys from Redis...")
        client = await get_redis_connection()
        
        # Get all conversation keys with pattern matching
        keys = await client.keys("conversation:*")
        logger.info(f"Found {len(keys)} conversation keys")
        
        if not keys:
            return []
        
        # Use pipeline for better performance
        pipe = client.pipeline()
        for key in keys:
            pipe.get(key)
        results = await pipe.execute()
        
        conversations = []
        for key, data in zip(keys, results):
            if not data:
                continue
                
            try:
                conversation = json.loads(data)
                if not isinstance(conversation, dict) or 'id' not in conversation:
                    logger.warning(f"Invalid conversation structure for key {key}")
                    continue
                    
                # Validate and sanitize conversation data
                conversation = sanitize_conversation(conversation)
                conversations.append(conversation)
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding conversation {key}: {str(e)}")
                continue
            except Exception as e:
                logger.error(f"Error processing conversation {key}: {str(e)}")
                continue
        
        # Sort conversations by updated_at
        conversations.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        logger.info(f"Successfully retrieved {len(conversations)} conversations")
        return conversations
        
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {str(e)}")
        raise RedisError("Failed to connect to Redis") from e
    except redis.TimeoutError as e:
        logger.error(f"Redis timeout error: {str(e)}")
        raise RedisError("Redis operation timed out") from e
    except Exception as e:
        logger.error(f"Unexpected error getting conversations: {str(e)}\n{traceback.format_exc()}")
        raise RedisError(f"Failed to get conversations: {str(e)}") from e

def sanitize_conversation(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize and validate conversation data."""
    required_fields = {'id', 'title', 'messages', 'created_at', 'updated_at'}
    if not all(field in conversation for field in required_fields):
        raise ValueError("Missing required fields in conversation")
    
    # Ensure messages is a list
    if not isinstance(conversation['messages'], list):
        conversation['messages'] = []
    
    # Sanitize each message
    conversation['messages'] = [
        sanitize_message(msg) for msg in conversation['messages']
        if isinstance(msg, dict)
    ]
    
    return conversation

def sanitize_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize and validate message data."""
    if not isinstance(message, dict):
        return {'role': 'system', 'content': 'Invalid message format', 'timestamp': datetime.now().isoformat()}
    
    return {
        'role': str(message.get('role', 'system')),
        'content': str(message.get('content', '')),
        'timestamp': message.get('timestamp', datetime.now().isoformat())
    }

async def save_conversation(conversation: Dict[str, Any]) -> None:
    """Save a conversation to Redis with validation."""
    try:
        # Validate and sanitize conversation
        conversation = sanitize_conversation(conversation)
        
        client = await get_redis_connection()
        key = f"conversation:{conversation['id']}"
        
        # Update timestamps
        conversation['updated_at'] = datetime.now().isoformat()
        if 'created_at' not in conversation:
            conversation['created_at'] = conversation['updated_at']
        
        # Save with expiration (30 days)
        await client.setex(
            key,
            60 * 60 * 24 * 30,  # 30 days in seconds
            json.dumps(conversation)
        )
        logger.info(f"Successfully saved conversation {conversation['id']}")
        
    except Exception as e:
        logger.error(f"Error saving conversation: {str(e)}\n{traceback.format_exc()}")
        raise RedisError(f"Failed to save conversation: {str(e)}") from e

async def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation from Redis."""
    try:
        client = await get_redis_connection()
        key = f"conversation:{conversation_id}"
        deleted = await client.delete(key)
        logger.info(f"Successfully deleted conversation {conversation_id}")
        return bool(deleted)
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}\n{traceback.format_exc()}")
        raise RedisError(f"Failed to delete conversation: {str(e)}") from e

async def delete_all_conversations() -> int:
    """Delete all conversations from Redis."""
    try:
        client = await get_redis_connection()
        keys = await client.keys("conversation:*")
        if not keys:
            return 0
            
        deleted = await client.delete(*keys)
        logger.info(f"Successfully deleted {deleted} conversations")
        return deleted
    except Exception as e:
        logger.error(f"Error deleting all conversations: {str(e)}\n{traceback.format_exc()}")
        raise RedisError(f"Failed to delete all conversations: {str(e)}") from e

async def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific conversation from Redis."""
    try:
        client = await get_redis_connection()
        key = f"conversation:{conversation_id}"
        data = await client.get(key)
        
        if not data:
            return None
            
        conversation = json.loads(data)
        return sanitize_conversation(conversation)
        
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding conversation data: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}\n{traceback.format_exc()}")
        raise RedisError(f"Failed to get conversation: {str(e)}") from e

async def health_check() -> Dict[str, Any]:
    """Check Redis connection health."""
    try:
        client = await get_redis_connection()
        await client.ping()
        info = await client.info()
        
        return {
            "status": "healthy",
            "redis_version": info.get("redis_version", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory_human", "unknown"),
            "uptime_days": info.get("uptime_in_days", 0)
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}\n{traceback.format_exc()}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__
        } 