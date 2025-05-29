import redis.asyncio as redis
import os
import json
from dotenv import load_dotenv
import logging
import traceback
from redis.asyncio.connection import ConnectionPool
import asyncio

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

async def get_redis_connection():
    """Get a Redis connection from the pool with retry logic"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            # Test the connection
            await redis_client.ping()
            return redis_client
        except (redis.ConnectionError, redis.TimeoutError) as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to connect to Redis after {max_retries} attempts: {str(e)}")
                raise
            logger.warning(f"Redis connection attempt {attempt + 1} failed: {str(e)}")
            await asyncio.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff

# Helper functions for Redis operations
async def get_conversations():
    """Get all conversations from Redis"""
    try:
        logger.info("Getting all conversation keys from Redis...")
        # Get a connection with retry logic
        client = await get_redis_connection()
        
        # Get all conversation keys
        try:
            keys = await client.keys("conversation:*")
            logger.info(f"Found {len(keys)} conversation keys")
        except Exception as e:
            logger.error(f"Failed to get conversation keys: {str(e)}\n{traceback.format_exc()}")
            raise
        
        if not keys:
            logger.info("No conversations found in Redis")
            return []
            
        # Get all conversations
        conversations = []
        for key in keys:
            try:
                logger.info(f"Fetching conversation from key: {key}")
                data = await client.get(key)
                if data:
                    try:
                        conversation = json.loads(data)
                        # Validate conversation structure
                        if isinstance(conversation, dict) and 'id' in conversation:
                            conversations.append(conversation)
                        else:
                            logger.warning(f"Invalid conversation structure for key {key}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding conversation {key}: {str(e)}\n{traceback.format_exc()}")
                        continue
            except Exception as e:
                logger.error(f"Error processing conversation {key}: {str(e)}\n{traceback.format_exc()}")
                continue
                
        # Sort conversations by updated_at in descending order
        conversations.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        logger.info(f"Successfully retrieved {len(conversations)} conversations")
        return conversations
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {str(e)}\n{traceback.format_exc()}")
        raise
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}\n{traceback.format_exc()}")
        return []

async def save_conversation(conversation):
    """Save a conversation to Redis"""
    try:
        key = f"conversation:{conversation['id']}"
        await redis_client.set(key, json.dumps(conversation))
    except Exception as e:
        print(f"Error saving conversation: {str(e)}")
        raise

async def delete_conversation(conversation_id):
    """Delete a conversation from Redis"""
    try:
        key = f"conversation:{conversation_id}"
        await redis_client.delete(key)
    except Exception as e:
        print(f"Error deleting conversation: {str(e)}")
        raise

async def delete_all_conversations():
    """Delete all conversations from Redis"""
    try:
        keys = await redis_client.keys("conversation:*")
        for key in keys:
            await redis_client.delete(key)
    except Exception as e:
        print(f"Error deleting all conversations: {str(e)}")
        raise

async def get_conversation(conversation_id):
    """Get a specific conversation from Redis"""
    try:
        key = f"conversation:{conversation_id}"
        data = await redis_client.get(key)
        return json.loads(data) if data else None
    except json.JSONDecodeError as e:
        print(f"Error decoding conversation data: {str(e)}")
        return None
    except Exception as e:
        print(f"Error getting conversation: {str(e)}")
        return None 