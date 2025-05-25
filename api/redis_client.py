import redis.asyncio as redis
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Redis connection details from environment variables
REDIS_URL = os.getenv("REDIS_URL")

# Initialize Redis client
redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True
)

# Helper functions for Redis operations
async def get_conversations():
    """Get all conversations from Redis"""
    keys = await redis_client.keys("conversation:*")
    conversations = []
    for key in keys:
        data = await redis_client.get(key)
        if data:
            conversations.append(eval(data))  # Convert string to dict
    return conversations

async def save_conversation(conversation):
    """Save a conversation to Redis"""
    key = f"conversation:{conversation['id']}"
    await redis_client.set(key, str(conversation))  # Convert dict to string

async def delete_conversation(conversation_id):
    """Delete a conversation from Redis"""
    key = f"conversation:{conversation_id}"
    await redis_client.delete(key)

async def delete_all_conversations():
    """Delete all conversations from Redis"""
    keys = await redis_client.keys("conversation:*")
    for key in keys:
        await redis_client.delete(key)

async def get_conversation(conversation_id):
    """Get a specific conversation from Redis"""
    key = f"conversation:{conversation_id}"
    data = await redis_client.get(key)
    return eval(data) if data else None 