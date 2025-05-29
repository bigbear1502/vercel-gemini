from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from redis_client import get_conversations
import json
import logging
import os
import traceback
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint to verify API is working"""
    try:
        return {"message": "Conversations API is running"}
    except Exception as e:
        logger.error(f"Error in root endpoint: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations")
async def get_all_conversations():
    try:
        logger.info("Received request to fetch conversations")
        
        # Check Redis connection
        try:
            conversations = await get_conversations()
            logger.info(f"Found {len(conversations) if conversations else 0} conversations")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {str(e)}\n{traceback.format_exc()}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "message": "Redis connection error",
                    "details": str(e),
                    "type": "connection_error"
                }
            )
        except redis.TimeoutError as e:
            logger.error(f"Redis timeout error: {str(e)}\n{traceback.format_exc()}")
            return JSONResponse(
                status_code=504,
                content={
                    "status": "error",
                    "message": "Redis timeout error",
                    "details": str(e),
                    "type": "timeout_error"
                }
            )
        except Exception as e:
            logger.error(f"Failed to get conversations from Redis: {str(e)}\n{traceback.format_exc()}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "message": "Failed to connect to Redis",
                    "details": str(e),
                    "type": "unknown_error"
                }
            )
        
        # Ensure conversations is a list
        if conversations is None:
            conversations = []
            
        # Convert any non-serializable objects to strings
        try:
            for conv in conversations:
                if 'messages' in conv:
                    for msg in conv['messages']:
                        if isinstance(msg, dict):
                            for key, value in msg.items():
                                if not isinstance(value, (str, int, float, bool, type(None))):
                                    msg[key] = str(value)
        except Exception as e:
            logger.error(f"Error processing conversation data: {str(e)}\n{traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Error processing conversation data",
                    "details": str(e)
                }
            )
        
        response = {
            "status": "success",
            "conversations": conversations
        }
        
        logger.info(f"Returning response with {len(conversations)} conversations")
        
        return JSONResponse(
            content=response,
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except Exception as e:
        logger.error(f"Error in get_all_conversations: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Internal server error while fetching conversations",
                "details": str(e)
            }
        )

@app.get("/api/conversations/health")
async def health_check():
    """Health check endpoint to verify API and Redis connectivity"""
    try:
        # Try to get conversations to test Redis connection
        try:
            await get_conversations()
            redis_status = "connected"
        except Exception as e:
            logger.error(f"Redis connection failed: {str(e)}\n{traceback.format_exc()}")
            redis_status = "disconnected"
            
        return JSONResponse(
            content={
                "status": "healthy" if redis_status == "connected" else "unhealthy",
                "message": "API is running",
                "redis_status": redis_status,
                "redis_url": os.getenv("REDIS_URL", "not set").split("@")[-1]  # Only show host part
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": "Service is not healthy",
                "details": str(e)
            }
        ) 