from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .redis_client import get_conversations
import json
import logging
import os

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
    return {"message": "Conversations API is running"}

@app.get("/api/conversations")
async def get_all_conversations():
    try:
        logger.info("Received request to fetch conversations")
        conversations = await get_conversations()
        logger.info(f"Found {len(conversations) if conversations else 0} conversations")
        
        # Ensure conversations is a list
        if conversations is None:
            conversations = []
            
        # Convert any non-serializable objects to strings
        for conv in conversations:
            if 'messages' in conv:
                for msg in conv['messages']:
                    if isinstance(msg, dict):
                        for key, value in msg.items():
                            if not isinstance(value, (str, int, float, bool, type(None))):
                                msg[key] = str(value)
        
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
        logger.error(f"Error in get_all_conversations: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Internal server error while fetching conversations",
                "details": str(e)
            },
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        )

@app.get("/api/conversations/health")
async def health_check():
    """Health check endpoint to verify API and Redis connectivity"""
    try:
        # Try to get conversations to test Redis connection
        await get_conversations()
        return JSONResponse(
            content={
                "status": "healthy",
                "message": "API and Redis connection are working",
                "redis_url": os.getenv("REDIS_URL", "not set").split("@")[-1]  # Only show host part
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "message": "Service is not healthy",
                "details": str(e)
            }
        ) 