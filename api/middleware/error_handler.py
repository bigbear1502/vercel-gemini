from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from ..redis_client import RedisError
import logging
import traceback
from typing import Callable
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def error_handler_middleware(request: Request, call_next: Callable):
    """Middleware to handle errors consistently across the application."""
    try:
        return await call_next(request)
    except RequestValidationError as e:
        # Handle validation errors
        logger.error(f"Validation error: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "message": "Validation error",
                "details": str(e),
                "error_type": "validation_error",
                "timestamp": datetime.now().isoformat()
            }
        )
    except RedisError as e:
        # Handle Redis-specific errors
        logger.error(f"Redis error: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "message": "Storage service unavailable",
                "details": str(e),
                "error_type": "storage_error",
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "An unexpected error occurred",
                "details": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            }
        ) 