from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
import os
from dotenv import load_dotenv
import uuid
from datetime import datetime
from .redis_client import (
    get_conversations,
    save_conversation,
    delete_conversation,
    delete_all_conversations,
    get_conversation
)

# Load environment variables
load_dotenv()

# Configure Google API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

genai.configure(api_key=GOOGLE_API_KEY)

# Initialize FastAPI app
app = FastAPI()

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

# Pydantic models
class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str

class Conversation(BaseModel):
    id: str
    title: str
    messages: List[Message]
    created_at: str
    updated_at: str

def get_available_model():
    """Try to get an available model that hasn't hit rate limits."""
    for model_name in AVAILABLE_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            # Test the model with a simple prompt
            model.generate_content("test")
            return model
        except Exception as e:
            print(f"Model {model_name} not available: {str(e)}")
            continue
    raise Exception("No available models found. Please try again later.")

@app.get("/api/models")
async def list_models():
    try:
        available_models = genai.list_models()
        model_names = [model.name for model in available_models]
        return {"available_models": model_names}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        user_message = request.message
        conversation_id = request.conversation_id
        
        # Get existing conversations
        conversations = await get_conversations()
        
        # Create a new conversation if none exists
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            new_conversation = {
                'id': conversation_id,
                'title': user_message[:30] + '...' if len(user_message) > 30 else user_message,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'messages': []
            }
            conversations.append(new_conversation)
        else:
            # Find existing conversation
            conversation = next((conv for conv in conversations if conv['id'] == conversation_id), None)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            conversation['updated_at'] = datetime.now().isoformat()
        
        # Add user message
        current_conversation = next((conv for conv in conversations if conv['id'] == conversation_id), None)
        current_conversation['messages'].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        try:
            # Try to get an available model
            model = get_available_model()
            response = model.generate_content(user_message)
            response_text = response.text
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            response_text = "I apologize, but I'm currently experiencing high demand. Please try again in a few moments."
        
        # Add AI response
        current_conversation['messages'].append({
            'role': 'assistant',
            'content': response_text,
            'timestamp': datetime.now().isoformat()
        })
        
        # Save updated conversations
        await save_conversation(current_conversation)
        
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/redis-health")
async def redis_health():
    try:
        # Test Redis connection
        await redis_client.ping()
        return {"status": "ok", "message": "Redis connection successful"}
    except Exception as e:
        print(f"Redis health check failed: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/api/conversations")
async def get_all_conversations():
    try:
        conversations = await get_conversations()
        return JSONResponse(
            content={
                "status": "success",
                "conversations": conversations or []
            },
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except Exception as e:
        print(f"Error in get_all_conversations: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            },
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
        )

@app.get("/api/conversations/{conversation_id}")
async def get_conversation_endpoint(conversation_id: str):
    try:
        conversation = await get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation_endpoint(conversation_id: str):
    try:
        await delete_conversation(conversation_id)
        return {"status": "success", "message": "Conversation deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/conversations")
async def delete_all_conversations_endpoint():
    try:
        await delete_all_conversations()
        return {"status": "success", "message": "All conversations deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/conversations/{conversation_id}/title")
async def update_conversation_title(conversation_id: str, title: str):
    try:
        conversation = await get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation["title"] = title
        conversation["updated_at"] = datetime.now().isoformat()
        
        await save_conversation(conversation)
        return {"status": "success", "message": "Title updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000) 