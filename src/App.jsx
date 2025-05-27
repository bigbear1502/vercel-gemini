import { useState, useRef, useEffect } from 'react';
import './App.css';

// Helper function to format text with Markdown-like structure
const formatText = (text) => {
  if (!text) return null;

  const lines = text.split('\n');
  const formattedElements = [];
  let currentList = null;
  let currentListItems = [];
  let currentIndentLevel = 0;
  let currentNumberedList = null;
  let currentNumberedItems = [];

  const processList = () => {
    if (currentListItems.length > 0) {
      formattedElements.push(
        <ul key={`list-${formattedElements.length}-${Date.now()}`} className="bullet-list">
          {currentListItems}
        </ul>
      );
      currentListItems = [];
    }
  };

  const processNumberedList = () => {
    if (currentNumberedItems.length > 0) {
      // Get the first number from the first item
      const firstNumber = currentNumberedItems[0].props['data-number'];
      formattedElements.push(
        <ol 
          key={`numbered-list-${formattedElements.length}-${Date.now()}`} 
          className="number-list"
          start={firstNumber}
        >
          {currentNumberedItems}
        </ol>
      );
      currentNumberedItems = [];
    }
  };

  const getIndentLevel = (line) => {
    const spaces = line.length - line.trimStart().length;
    return Math.floor(spaces / 2); // 2 spaces = 1 indent level
  };

  const processLinks = (text) => {
    return text.replace(/\[(.*?)\]\((.*?)\)/g, (match, text, url) => {
      return `<a href="${url}" target="_blank" rel="noopener noreferrer">${text}</a>`;
    });
  };

  const processBoldText = (text) => {
    // First process links
    text = processLinks(text);
    
    // Then process bold text
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      // Check if the part contains a link
      if (part.includes('<a href=')) {
        return <span key={i} dangerouslySetInnerHTML={{ __html: part }} />;
      }
      return part;
    });
  };

  lines.forEach((line, index) => {
    const trimmedLine = line.trim();
    const indentLevel = getIndentLevel(line);

    // Skip empty lines
    if (!trimmedLine) {
      processList();
      processNumberedList();
      return;
    }

    // Handle headers with proper spacing
    if (trimmedLine.startsWith('### ')) {
      processList();
      processNumberedList();
      formattedElements.push(
        <div key={index} className="header-section">
          <h3 className="main-content">
            {processBoldText(trimmedLine.replace('### ', ''))}
          </h3>
        </div>
      );
      return;
    }

    if (trimmedLine.startsWith('#### ')) {
      processList();
      processNumberedList();
      formattedElements.push(
        <div key={index} className="header-section">
          <h4 className="major-section">
            {processBoldText(trimmedLine.replace('#### ', ''))}
          </h4>
        </div>
      );
      return;
    }

    // Handle bullet points with proper indentation
    if (trimmedLine.startsWith('* ')) {
      processNumberedList();
      const content = trimmedLine.replace(/^\*\s+/, '');
      
      // If indentation level changed, process the current list
      if (indentLevel !== currentIndentLevel) {
        processList();
        currentIndentLevel = indentLevel;
      }

      currentListItems.push(
        <li 
          key={currentListItems.length} 
          style={{ 
            marginLeft: `${indentLevel * 20}px`,
            listStyleType: indentLevel === 0 ? 'disc' : 'circle'
          }}
        >
          {processBoldText(content)}
        </li>
      );
      return;
    }

    // Handle numbered lists with proper indentation
    if (/^\d+\.\s/.test(trimmedLine)) {
      processList();
      const match = trimmedLine.match(/^(\d+)\.\s+(.*)/);
      if (match) {
        const [, number, content] = match;
        
        // If indentation level changed, process the current numbered list
        if (indentLevel !== currentIndentLevel) {
          processNumberedList();
          currentIndentLevel = indentLevel;
        }

        currentNumberedItems.push(
          <li 
            key={currentNumberedItems.length}
            style={{ marginLeft: `${indentLevel * 20}px` }}
            data-number={parseInt(number)}
          >
            {processBoldText(content)}
          </li>
        );
      }
      return;
    }

    // Handle bold text and links in regular paragraphs with proper spacing
    if (trimmedLine.includes('**') || trimmedLine.includes('[')) {
      processList();
      processNumberedList();
      formattedElements.push(
        <div key={index} className="paragraph-section" style={{ marginLeft: `${indentLevel * 20}px` }}>
          <p>
            {processBoldText(trimmedLine)}
          </p>
        </div>
      );
      return;
    }

    // Regular text with proper indentation
    processList();
    processNumberedList();
    formattedElements.push(
      <div key={index} className="paragraph-section" style={{ marginLeft: `${indentLevel * 20}px` }}>
        <p>{trimmedLine}</p>
      </div>
    );
  });

  // Process any remaining lists
  processList();
  processNumberedList();

  return formattedElements;
};

// Helper function to format inline text (bold, italic, links)
const formatInlineText = (text) => {
  // Handle bold text
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // Handle italic text
  text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
  
  // Handle links
  text = text.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  
  // Handle highlighted text
  text = text.replace(/==(.*?)==/g, '<mark>$1</mark>');
  
  // Remove any remaining asterisks
  text = text.replace(/\*/g, '');
  
  return <span dangerouslySetInnerHTML={{ __html: text }} />;
};

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const messagesEndRef = useRef(null);

  // Fetch conversations on component mount
  useEffect(() => {
    fetchConversations();
  }, []);

  // Auto-scroll to bottom when new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchConversations = async () => {
    try {
      const response = await fetch('/api/conversations', {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        console.error('Invalid content type:', contentType);
        throw new TypeError("Server returned non-JSON response");
      }
      
      const data = await response.json();
      if (data && data.status === 'success' && Array.isArray(data.conversations)) {
        setConversations(data.conversations);
      } else {
        console.error('Unexpected response format:', data);
        setConversations([]);
      }
    } catch (error) {
      console.error('Error fetching conversations:', error);
      setConversations([]);
    }
  };

  const loadConversation = async (conversationId) => {
    try {
      const response = await fetch(`/api/conversations/${conversationId}`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const conversation = await response.json();
      setMessages(conversation.messages || []);
      setCurrentConversationId(conversationId);
    } catch (error) {
      console.error('Error loading conversation:', error);
      setMessages([]);
      setCurrentConversationId(null);
    }
  };

  const startNewConversation = () => {
    setMessages([]);
    setCurrentConversationId(null);
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    setIsLoading(true);
    const userMessage = input.trim();
    setInput('');

    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage,
          conversation_id: currentConversationId
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Add AI response to messages
      if (data.response) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
      }

      if (data.conversation_id) {
        setCurrentConversationId(data.conversation_id);
        await fetchConversations(); // Refresh conversations list
      }
    } catch (error) {
      console.error('Error sending message:', error);
      // Add error message
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, there was an error processing your request. Please try again.' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteConversation = async (conversationId) => {
    try {
      const response = await fetch(`/api/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await fetchConversations();
      if (currentConversationId === conversationId) {
        setMessages([]);
        setCurrentConversationId(null);
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  const deleteAllConversations = async () => {
    try {
      const response = await fetch('/api/conversations', {
        method: 'DELETE',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setConversations([]);
      setMessages([]);
      setCurrentConversationId(null);
      setShowDeleteConfirm(false);
    } catch (error) {
      console.error('Error deleting all conversations:', error);
    }
  };

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h2>Chat History</h2>
          <div className="sidebar-actions">
            <button 
              onClick={startNewConversation} 
              className="new-chat-btn"
              title="Start new chat"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14" />
              </svg>
              New Chat
            </button>
            <button 
              onClick={() => setShowDeleteConfirm(true)} 
              className="delete-all-btn"
              title="Delete all conversations"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Clear All
            </button>
          </div>
        </div>
        <div className="conversations-list">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${conv.id === currentConversationId ? 'active' : ''}`}
            >
              <div 
                className="conversation-content"
                onClick={() => loadConversation(conv.id)}
              >
                <h3>{conv.title}</h3>
                <p>{new Date(conv.updated_at).toLocaleDateString()}</p>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteConversation(conv.id);
                }}
                className="delete-btn"
                title="Delete conversation"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      </aside>

      {showDeleteConfirm && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Delete All Conversations</h3>
            <p>Are you sure you want to delete all conversations? This action cannot be undone.</p>
            <div className="modal-actions">
              <button onClick={deleteAllConversations} className="confirm-btn">
                Delete All
              </button>
              <button onClick={() => setShowDeleteConfirm(false)} className="cancel-btn">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <main className="chat-container">
        <div className="chat-header">
          <div className="logo-container">
            <svg className="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <h1>Chatbot Assistant</h1>
          </div>
          <p className="slogan">Your AI-powered conversation partner</p>
        </div>
        <div className="chat-messages">
          {messages.length === 0 ? (
            <div className="empty-state">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <p>Start a conversation with the AI Assistant</p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div 
                key={index} 
                className={`message ${message.role === 'user' ? 'user-message' : 'ai-message'}`}
              >
                <div className="message-avatar">
                  {message.role === 'user' ? (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  )}
                </div>
                <div className="message-content">
                  {message.role === 'user' ? (
                    <p>{message.content}</p>
                  ) : (
                    formatText(message.content)
                  )}
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="message ai-message">
              <div className="message-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="message-content">
                <div className="loading-indicator">
                  <div className="dot"></div>
                  <div className="dot"></div>
                  <div className="dot"></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="chat-input-form">
          <input
            type="text"
            value={input}
            onChange={handleInputChange}
            placeholder="Type your message..."
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || input.trim() === ''}>
            {isLoading ? (
              <svg className="loading-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            )}
          </button>
        </form>
      </main>
    </div>
  );
}

export default App; 