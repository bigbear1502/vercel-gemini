# Chatbot Assistant with Gemini AI

A modern chat application built with React (Vite) frontend and Python (FastAPI) backend, deployed on Vercel.

## Features

- Real-time chat interface with Gemini AI
- Conversation history management
- Markdown-like text formatting
- Responsive design
- Loading states and error handling
- Conversation persistence

## Tech Stack

- Frontend:

  - React (Vite)
  - CSS3 with modern features
  - Responsive design

- Backend:
  - Python (FastAPI)
  - Google Gemini AI
  - JSON file-based storage

## Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/chatbot-gemini-vercel.git
cd chatbot-gemini-vercel
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

3. Install Node.js dependencies:

```bash
npm install
```

4. Create a `.env` file in the root directory:

```
GOOGLE_API_KEY=your_api_key_here
```

5. For local development:
   - Start the Python backend: `uvicorn api.chat:app --reload`
   - Start the React frontend: `npm run dev`

## Deployment

The application is configured for deployment on Vercel. Make sure to:

1. Set up your environment variables in the Vercel dashboard
2. Connect your GitHub repository
3. Deploy using the Vercel CLI or through the Vercel dashboard

## License

MIT
