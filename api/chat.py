from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

# Available models
MODELS = [
    'gemini-2.0-flash',  # Fastest, good for most use cases
    'gemini-1.5-pro',    # More capable but slower
    'gemini-1.0-pro'     # Fallback option
]

# Pydantic models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: str = "gemini-pro"

class ChatResponse(BaseModel):
    response: str
    conversation_id: str

class Conversation(BaseModel):
    id: str
    title: str
    messages: List[Message]
    created_at: str
    updated_at: str

# Helper function to generate response
def generate_response(messages: List[Message], model_name: str = "gemini-2.0-flash") -> str:
    try:
        model = genai.GenerativeModel(model_name)
        chat = model.start_chat(history=[])
        
        for msg in messages:
            if msg.role == "user":
                chat.send_message(msg.content)
            else:
                # Add assistant messages to history
                chat.history.append({"role": "model", "parts": [msg.content]})
        
        response = chat.last.text
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
async def list_models():
    return {"models": MODELS}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Get or create conversation
        if request.conversation_id:
            current_conversation = await get_conversation(request.conversation_id)
            if not current_conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            current_conversation = {
                "id": str(uuid.uuid4()),
                "title": request.message[:30] + "..." if len(request.message) > 30 else request.message,
                "messages": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

        # Add user message
        current_conversation["messages"].append({
            "role": "user",
            "content": request.message
        })

        try:
            # Generate response
            response = generate_response(current_conversation["messages"], request.model)

            # Add assistant message
            current_conversation["messages"].append({
                "role": "assistant",
                "content": response
            })

            # Update timestamp
            current_conversation["updated_at"] = datetime.now().isoformat()

            # Save conversation
            await save_conversation(current_conversation)

            return {
                "status": "success",
                "response": response,
                "conversation_id": current_conversation["id"]
            }

        except Exception as e:
            print(f"Error generating response: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error generating response: {str(e)}"
            )

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

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
        return {
            "status": "success",
            "conversations": conversations or []
        }
    except Exception as e:
        print(f"Error in get_all_conversations: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
            headers={"Content-Type": "application/json"}
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