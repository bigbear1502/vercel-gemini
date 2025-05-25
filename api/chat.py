from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import uuid
from datetime import datetime
import re

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicitly list allowed methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"]  # Exposes all headers
)

# Configure the Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("No GOOGLE_API_KEY found in environment variables")

# Configure the generative AI model
genai.configure(api_key=GOOGLE_API_KEY)

# List of models to try in order of preference
AVAILABLE_MODELS = [
    'gemini-2.0-flash',  # Fastest, good for most use cases
    'gemini-1.5-pro',    # More capable but slower
    'gemini-1.0-pro'     # Fallback option
]

# File to store conversations
CONVERSATIONS_FILE = "conversations.json"

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str

def get_conversations():
    if os.path.exists(CONVERSATIONS_FILE):
        try:
            with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_conversations(conversations):
    with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)

# Get available models for debugging
@app.get("/models")
def list_models():
    try:
        available_models = genai.list_models()
        model_names = [model.name for model in available_models]
        return {"available_models": model_names}
    except Exception as e:
        return {"error": str(e)}, 500

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

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        user_message = request.message
        conversation_id = request.conversation_id
        
        # Get existing conversations
        conversations = get_conversations()
        
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
        save_conversations(conversations)
        
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "ok"}, 200

@app.get("/debug")
def debug_info():
    try:
        # Check if API key is set
        api_key_status = "Set" if GOOGLE_API_KEY else "Not set"
        
        # Try to validate API key (this doesn't make an actual model call)
        api_key_valid = "Unknown"
        try:
            # Just check if we can get the models list
            _ = genai.list_models()
            api_key_valid = "Valid"
        except Exception as e:
            api_key_valid = f"Invalid: {str(e)}"
        
        return {
            "api_key_status": api_key_status,
            "api_key_valid": api_key_valid,
            "google_ai_package_version": genai.__version__
        }
    except Exception as e:
        return {"error": str(e)}, 500

# Endpoint to get all conversations
@app.get("/conversations")
def get_all_conversations():
    try:
        conversations = get_conversations()
        return {"conversations": conversations}
    except Exception as e:
        print(f"Error getting conversations: {str(e)}")
        return {"error": str(e)}, 500

# Endpoint to get a specific conversation
@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    try:
        conversations = get_conversations()
        conversation = next((conv for conv in conversations if conv['id'] == conversation_id), None)
        
        if not conversation:
            return {"error": "Conversation not found"}, 404
        
        return conversation
    except Exception as e:
        print(f"Error getting conversation: {str(e)}")
        return {"error": str(e)}, 500

# Endpoint to delete a conversation
@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    try:
        conversations = get_conversations()
        conversations = [conv for conv in conversations if conv['id'] != conversation_id]
        save_conversations(conversations)
        return {"message": "Conversation deleted successfully"}, 200
    except Exception as e:
        print(f"Error deleting conversation: {str(e)}")
        return {"error": str(e)}, 500

# Endpoint to delete all conversations
@app.delete("/conversations")
def delete_all_conversations():
    try:
        save_conversations([])
        return {"message": "All conversations deleted successfully"}, 200
    except Exception as e:
        print(f"Error deleting all conversations: {str(e)}")
        return {"error": str(e)}, 500

# Endpoint to update conversation title
@app.put("/conversations/{conversation_id}/title")
def update_conversation_title(conversation_id: str):
    try:
        data = request.get_json()
        if not data or 'title' not in data:
            return {"error": "No title provided"}, 400
        
        conversations = get_conversations()
        conversation = next((conv for conv in conversations if conv['id'] == conversation_id), None)
        
        if not conversation:
            return {"error": "Conversation not found"}, 404
        
        conversation['title'] = data['title']
        save_conversations(conversations)
        
        return {"success": True}
    except Exception as e:
        print(f"Error updating conversation title: {str(e)}")
        return {"error": str(e)}, 500

def handler(request):
    return app(request)

if __name__ == '__main__':
    app.run(debug=True, port=5000) 