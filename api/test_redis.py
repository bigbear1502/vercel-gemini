import asyncio
import os
from dotenv import load_dotenv
import redis.asyncio as redis

# Load environment variables
load_dotenv()

# Get Redis connection details from environment variables
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("REDIS_URL environment variable is not set")

async def test_redis_connection():
    try:
        # Initialize Redis client
        print(f"Connecting to Redis at: {REDIS_URL}")
        redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        
        # Test connection
        print("Testing connection...")
        await redis_client.ping()
        print("✅ Successfully connected to Redis!")
        
        # Test write
        print("\nTesting write operation...")
        test_key = "test:connection"
        await redis_client.set(test_key, "Hello from Python!")
        print("✅ Successfully wrote to Redis!")
        
        # Test read
        print("\nTesting read operation...")
        value = await redis_client.get(test_key)
        print(f"✅ Successfully read from Redis: {value}")
        
        # Clean up
        await redis_client.delete(test_key)
        print("\n✅ Test completed successfully!")
        
    except redis.ConnectionError as e:
        print(f"❌ Redis connection error: {str(e)}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        if 'redis_client' in locals():
            await redis_client.close()

if __name__ == "__main__":
    asyncio.run(test_redis_connection()) 