import redis.asyncio as redis
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Redis connection details from environment variables
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("REDIS_URL environment variable is not set")

# Initialize Redis client
try:
    redis_client = redis.from_url(
        REDIS_URL,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5
    )
except Exception as e:
    print(f"Error connecting to Redis: {str(e)}")
    raise

# Helper functions for Redis operations
async def get_conversations():
    """Get all conversations from Redis"""
    try:
        keys = await redis_client.keys("conversation:*")
        conversations = []
        for key in keys:
            data = await redis_client.get(key)
            if data:
                try:
                    conversations.append(json.loads(data))
                except json.JSONDecodeError as e:
                    print(f"Error decoding conversation data: {str(e)}")
                    continue
        return conversations
    except Exception as e:
        print(f"Error getting conversations: {str(e)}")
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