from fastapi import Request, status
from fastapi.responses import JSONResponse
import time
import logging
from datetime import datetime
from typing import Dict, Tuple, Callable
import asyncio
from redis_client import get_redis_connection, RedisError

logger = logging.getLogger(__name__)

# Rate limit configuration
RATE_LIMIT_WINDOW = 60  # 1 minute window
MAX_REQUESTS_PER_WINDOW = 60  # 60 requests per minute
RATE_LIMIT_KEY_PREFIX = "rate_limit:"

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass

async def get_client_identifier(request: Request) -> str:
    """Get a unique identifier for the client."""
    # Try to get the real IP address
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Get the first IP in the chain
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    
    return f"{client_ip}"

async def check_rate_limit(client_id: str) -> Tuple[bool, int]:
    """Check if the client has exceeded the rate limit."""
    try:
        client = await get_redis_connection()
        key = f"{RATE_LIMIT_KEY_PREFIX}{client_id}"
        
        # Get current count and window start
        pipe = client.pipeline()
        pipe.get(key)
        pipe.ttl(key)
        count, ttl = await pipe.execute()
        
        current_time = int(time.time())
        
        if count is None:
            # First request in the window
            await client.setex(key, RATE_LIMIT_WINDOW, 1)
            return True, RATE_LIMIT_WINDOW
        
        count = int(count)
        if count >= MAX_REQUESTS_PER_WINDOW:
            # Rate limit exceeded
            return False, ttl
        
        # Increment counter
        await client.incr(key)
        return True, ttl
        
    except RedisError as e:
        logger.error(f"Redis error in rate limit check: {str(e)}")
        # If Redis is down, allow the request but log the error
        return True, 0
    except Exception as e:
        logger.error(f"Error in rate limit check: {str(e)}")
        # On any other error, allow the request but log the error
        return True, 0

async def rate_limit_middleware(request: Request, call_next: Callable):
    """Middleware to implement rate limiting."""
    # Skip rate limiting for health check endpoints
    if request.url.path in ["/api/health", "/api/redis-health"]:
        return await call_next(request)
    
    try:
        client_id = await get_client_identifier(request)
        allowed, ttl = await check_rate_limit(client_id)
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for client {client_id}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "status": "error",
                    "message": "Rate limit exceeded",
                    "details": f"Please try again in {ttl} seconds",
                    "error_type": "rate_limit_exceeded",
                    "retry_after": ttl,
                    "timestamp": datetime.now().isoformat()
                },
                headers={"Retry-After": str(ttl)}
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(MAX_REQUESTS_PER_WINDOW)
        response.headers["X-RateLimit-Remaining"] = str(MAX_REQUESTS_PER_WINDOW - int(await get_redis_connection().get(f"{RATE_LIMIT_KEY_PREFIX}{client_id}") or 0))
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + ttl)
        return response
        
    except Exception as e:
        logger.error(f"Error in rate limit middleware: {str(e)}")
        # On any error, allow the request but log the error
        return await call_next(request) 