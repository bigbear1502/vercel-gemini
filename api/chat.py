from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
import google.generativeai as genai
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime
import logging
import traceback
from .redis_client import (
    get_conversations,
    save_conversation,
    delete_conversation,
    delete_all_conversations,
    get_conversation,
    RedisError,
    health_check as redis_health_check
)
from .middleware.rate_limit import rate_limit_middleware
from .middleware.error_handler import error_handler_middleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Google API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

genai.configure(api_key=GOOGLE_API_KEY)

# Initialize FastAPI app
app = FastAPI(
    title="Chatbot API",
    description="A chatbot API powered by Google's Gemini model",
    version="1.0.0"
)

# Add middlewares
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(error_handler_middleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# List of models to try in order of preference
AVAILABLE_MODELS = [
    'gemini-2.0-flash',  # Fastest, good for most use cases
    'gemini-1.5-pro',    # More capable but slower
    'gemini-1.0-pro'     # Fallback option
]

class Message(BaseModel):
    role: str = Field(..., description="The role of the message sender (user/assistant)")
    content: str = Field(..., description="The content of the message")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ['user', 'assistant', 'system']:
            raise ValueError('Role must be user, assistant, or system')
        return v

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="The user's message")
    conversation_id: Optional[str] = Field(None, description="The ID of the existing conversation")

    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty or whitespace')
        return v.strip()

class ChatResponse(BaseModel):
    response: str = Field(..., description="The AI's response message")
    conversation_id: str = Field(..., description="The ID of the conversation")
    status: str = Field(default="success", description="The status of the response")

class Conversation(BaseModel):
    id: str = Field(..., description="The unique identifier of the conversation")
    title: str = Field(..., description="The title of the conversation")
    messages: List[Message] = Field(..., description="The list of messages in the conversation")
    created_at: str = Field(..., description="The creation timestamp")
    updated_at: str = Field(..., description="The last update timestamp")

    @field_validator('messages')
    @classmethod
    def validate_messages(cls, v):
        if not isinstance(v, list):
            raise ValueError('Messages must be a list')
        return v

class ErrorResponse(BaseModel):
    status: str = Field(default="error", description="The status of the response")
    message: str = Field(..., description="The error message")
    details: Optional[str] = Field(None, description="Additional error details")
    error_type: Optional[str] = Field(None, description="The type of error")

def get_available_model():
    """Get an available model with fallback options."""
    for model_name in AVAILABLE_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            return model
        except Exception as e:
            logger.warning(f"Failed to load model {model_name}: {str(e)}")
            continue
    raise RuntimeError("No available models found")

@app.post("/api/chat", response_model=ChatResponse, responses={500: {"model": ErrorResponse}})
async def chat_endpoint(request: ChatRequest):
    """Process a chat message and return the response."""
    try:
        user_message = request.message
        conversation_id = request.conversation_id
        
        # Get existing conversation if ID provided
        conversation = None
        if conversation_id:
            try:
                conversation = await get_conversation(conversation_id)
                if not conversation:
                    raise HTTPException(status_code=404, detail="Conversation not found")
            except RedisError as e:
                logger.error(f"Redis error while getting conversation: {str(e)}")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "status": "error",
                        "message": "Failed to access conversation storage",
                        "details": str(e),
                        "error_type": "storage_error"
                    }
                )
        
        # Generate AI response first
        try:
            model = get_available_model()
            response = model.generate_content(user_message)
            response_text = response.text
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}\n{traceback.format_exc()}")
            response_text = "I apologize, but I'm currently experiencing technical difficulties. Please try again in a few moments."
        
        # Create or update conversation after getting AI response
        if not conversation:
            # Generate new conversation ID only after successful AI response
            conversation_id = str(uuid.uuid4())
            conversation = {
                'id': conversation_id,
                'title': user_message[:30] + '...' if len(user_message) > 30 else user_message,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'messages': []
            }
        
        # Add messages to conversation
        conversation['messages'].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        conversation['messages'].append({
            'role': 'assistant',
            'content': response_text,
            'timestamp': datetime.now().isoformat()
        })
        
        # Save conversation to Redis
        try:
            await save_conversation(conversation)
        except RedisError as e:
            logger.error(f"Redis error while saving conversation: {str(e)}")
            # Don't raise an error here, as the chat was successful
            # Just log the error and continue
        
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            status="success"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "An unexpected error occurred",
                "details": str(e),
                "error_type": type(e).__name__
            }
        )

@app.get("/api/health")
async def health_check():
    """Check the health of the API and Redis connection."""
    try:
        # Check Redis health
        redis_status = await redis_health_check()
        
        # Check Google API
        try:
            model = get_available_model()
            google_api_status = "healthy"
        except Exception as e:
            logger.error(f"Google API health check failed: {str(e)}")
            google_api_status = "unhealthy"
        
        return {
            "status": "healthy" if redis_status["status"] == "healthy" and google_api_status == "healthy" else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "redis": redis_status,
                "google_api": {
                    "status": google_api_status
                }
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}\n{traceback.format_exc()}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "error_type": type(e).__name__
        }

@app.get("/api/conversations/{conversation_id}", response_model=Conversation, responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_conversation_endpoint(conversation_id: str):
    """Get a specific conversation by ID."""
    try:
        conversation = await get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "message": "Conversation not found",
                    "error_type": "not_found"
                }
            )
        return conversation
    except RedisError as e:
        logger.error(f"Redis error while getting conversation: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": "Failed to fetch conversation",
                "details": str(e),
                "error_type": "storage_error"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_conversation_endpoint: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "An unexpected error occurred",
                "details": str(e),
                "error_type": type(e).__name__
            }
        )

@app.delete("/api/conversations/{conversation_id}", responses={500: {"model": ErrorResponse}})
async def delete_conversation_endpoint(conversation_id: str):
    """Delete a specific conversation."""
    try:
        deleted = await delete_conversation(conversation_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "message": "Conversation not found",
                    "error_type": "not_found"
                }
            )
        return {"status": "success", "message": "Conversation deleted"}
    except RedisError as e:
        logger.error(f"Redis error while deleting conversation: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": "Failed to delete conversation",
                "details": str(e),
                "error_type": "storage_error"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in delete_conversation_endpoint: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "An unexpected error occurred",
                "details": str(e),
                "error_type": type(e).__name__
            }
        )

@app.delete("/api/conversations", responses={500: {"model": ErrorResponse}})
async def delete_all_conversations_endpoint():
    """Delete all conversations."""
    try:
        deleted_count = await delete_all_conversations()
        return {
            "status": "success",
            "message": f"Deleted {deleted_count} conversations"
        }
    except RedisError as e:
        logger.error(f"Redis error while deleting all conversations: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": "Failed to delete conversations",
                "details": str(e),
                "error_type": "storage_error"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in delete_all_conversations_endpoint: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "An unexpected error occurred",
                "details": str(e),
                "error_type": type(e).__name__
            }
        )

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000) 