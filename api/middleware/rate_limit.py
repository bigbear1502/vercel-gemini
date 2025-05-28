from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import time
from typing import Dict, Tuple
import asyncio
from redis_client import redis_client

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = {}

    async def is_rate_limited(self, client_id: str) -> bool:
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window

        # Get existing requests from Redis
        key = f"rate_limit:{client_id}"
        requests = await redis_client.lrange(key, 0, -1)
        requests = [float(r) for r in requests]

        # Remove old requests
        requests = [r for r in requests if r > window_start]

        # Check if rate limit is exceeded
        if len(requests) >= self.requests_per_minute:
            return True

        # Add new request
        await redis_client.lpush(key, current_time)
        await redis_client.expire(key, 60)  # Expire after 1 minute

        return False

rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    client_id = request.client.host

    if await rate_limiter.is_rate_limited(client_id):
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too many requests",
                "message": "Please try again in a minute"
            }
        )

    response = await call_next(request)
    return response 