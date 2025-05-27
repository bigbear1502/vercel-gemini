from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .redis_client import get_conversations
import json

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
async def get_all_conversations():
    try:
        print("Fetching conversations from Redis...")
        conversations = await get_conversations()
        print(f"Found {len(conversations) if conversations else 0} conversations")
        
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
        
        print(f"Returning response: {json.dumps(response)[:200]}...")  # Log first 200 chars
        
        return JSONResponse(
            content=response,
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