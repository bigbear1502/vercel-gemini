import asyncio
import uuid
import argparse
from datetime import datetime
from redis_client import save_conversation, delete_all_conversations

# Example conversations to seed
EXAMPLE_CONVERSATIONS = [
    {
        "id": str(uuid.uuid4()),
        "title": "Introduction to AI",
        "messages": [
            {
                "role": "user",
                "content": "What is artificial intelligence?",
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "assistant",
                "content": "Artificial Intelligence (AI) is the simulation of human intelligence by machines that are programmed to think and learn like humans. It encompasses a wide range of technologies and approaches that enable computers to perform tasks that typically require human intelligence, such as visual perception, speech recognition, decision-making, and language translation.",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Python Programming",
        "messages": [
            {
                "role": "user",
                "content": "How do I write a simple Python function?",
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "assistant",
                "content": "Here's a simple example of a Python function:\n\ndef greet(name):\n    return f'Hello, {name}!'\n\nYou can call it like this:\nprint(greet('Alice'))  # Output: Hello, Alice!",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Web Development",
        "messages": [
            {
                "role": "user",
                "content": "What are the main components of a web application?",
                "timestamp": datetime.now().isoformat()
            },
            {
                "role": "assistant",
                "content": "A typical web application consists of several key components:\n\n1. Frontend (Client-side):\n   - HTML for structure\n   - CSS for styling\n   - JavaScript for interactivity\n\n2. Backend (Server-side):\n   - Server (e.g., Node.js, Python, Java)\n   - Database (e.g., MySQL, MongoDB)\n   - API endpoints\n\n3. Additional components:\n   - Authentication system\n   - File storage\n   - Caching layer\n   - Load balancer",
                "timestamp": datetime.now().isoformat()
            }
        ],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
]

async def seed_examples(clear_existing=False):
    try:
        if clear_existing:
            # Clear existing conversations
            await delete_all_conversations()
            print("Cleared existing conversations")

        # Add example conversations
        for conversation in EXAMPLE_CONVERSATIONS:
            await save_conversation(conversation)
            print(f"Added conversation: {conversation['title']}")

        print("Successfully seeded example conversations!")
    except Exception as e:
        print(f"Error seeding examples: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Seed example conversations in Redis')
    parser.add_argument('--clear', action='store_true', help='Clear existing conversations before seeding')
    args = parser.parse_args()
    
    asyncio.run(seed_examples(args.clear)) 