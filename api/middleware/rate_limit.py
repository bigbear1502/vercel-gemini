from fastapi import Request, status
from fastapi.responses import JSONResponse
import time
import logging
from datetime import datetime
from typing import Dict, Tuple, Callable
import asyncio
from ..redis_client import get_redis_connection, RedisError

logger = logging.getLogger(__name__)

# Rate limit configuration
RATE_LIMIT_WINDOW = 60  # 1 minute window
MAX_REQUESTS_PER_WINDOW = 60  # 60 requests per minute
RATE_LIMIT_KEY_PREFIX = "rate_limit:"

# Cache for rate limit info to reduce Redis calls
_rate_limit_cache: Dict[str, Tuple[int, int]] = {}  # client_id -> (count, expiry)
_cache_ttl = 5  # seconds to cache rate limit info

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

async def check_rate_limit(client_id: str) -> Tuple[bool, int, int]:
    """Check if the client has exceeded the rate limit. Returns (allowed, remaining, ttl)."""
    current_time = int(time.time())
    
    # Check cache first
    if client_id in _rate_limit_cache:
        count, expiry = _rate_limit_cache[client_id]
        if current_time < expiry:
            remaining = MAX_REQUESTS_PER_WINDOW - count
            return count < MAX_REQUESTS_PER_WINDOW, remaining, expiry - current_time
    
    try:
        client = await get_redis_connection()
        key = f"{RATE_LIMIT_KEY_PREFIX}{client_id}"
        
        # Use a single pipeline for all operations
        pipe = client.pipeline()
        pipe.get(key)
        pipe.ttl(key)
        pipe.incr(key)
        pipe.expire(key, RATE_LIMIT_WINDOW)
        count, ttl, new_count, _ = await pipe.execute()
        
        # Update cache
        _rate_limit_cache[client_id] = (new_count, current_time + ttl)
        
        # Clean old cache entries
        if len(_rate_limit_cache) > 1000:  # Prevent unbounded growth
            _rate_limit_cache.clear()
        
        remaining = MAX_REQUESTS_PER_WINDOW - new_count
        return new_count <= MAX_REQUESTS_PER_WINDOW, remaining, ttl
        
    except RedisError as e:
        logger.error(f"Redis error in rate limit check: {str(e)}")
        return True, MAX_REQUESTS_PER_WINDOW, 0
    except Exception as e:
        logger.error(f"Error in rate limit check: {str(e)}")
        return True, MAX_REQUESTS_PER_WINDOW, 0

async def rate_limit_middleware(request: Request, call_next: Callable):
    """Middleware to implement rate limiting."""
    # Skip rate limiting for health check endpoints
    if request.url.path in ["/api/health", "/api/redis-health"]:
        return await call_next(request)
    
    try:
        client_id = await get_client_identifier(request)
        allowed, remaining, ttl = await check_rate_limit(client_id)
        
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
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + ttl)
        return response
        
    except Exception as e:
        logger.error(f"Error in rate limit middleware: {str(e)}")
        # On any error, allow the request but log the error
        return await call_next(request) 