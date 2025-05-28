from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from conversations import app as conversations_app
from chat import app as chat_app

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers from both apps
app.include_router(conversations_app.router)
app.include_router(chat_app.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 