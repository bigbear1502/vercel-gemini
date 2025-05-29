import { useState, useRef, useEffect } from 'react';
import './App.css';
import ChatMessage from './components/ChatMessage';
import ConversationList from './components/ConversationList';
import { formatText } from './components/TextFormatter';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmConfig, setDeleteConfirmConfig] = useState({
    show: false,
    conversationId: null,
    dontShowAgain: false
  });
  const [input, setInput] = useState('');
  const [localMessages, setLocalMessages] = useState([]);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    fetchConversations();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [conversations, localMessages]);

  // Keep input focused after sending message
  useEffect(() => {
    if (!isLoading && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isLoading]);

  const handleInputChange = (e) => {
    setInput(e.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const message = input.trim();
    setInput('');
    setIsLoading(true);
    setError(null);

    // Add user message immediately to local state
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };
    setLocalMessages(prev => [...prev, userMessage]);

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          ...(currentConversationId && { conversation_id: currentConversationId })
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to send message');
      }
      
      const data = await response.json();
      if (data.status === 'success' && data.conversation_id) {
        // Add AI response to local state
        const aiMessage = {
          role: 'assistant',
          content: data.response,
          timestamp: new Date().toISOString()
        };
        setLocalMessages(prev => [...prev, aiMessage]);
        
        // Update conversation ID and refresh conversations
        setCurrentConversationId(data.conversation_id);
        await fetchConversations();
        
        // Clear local messages after successful save
        setLocalMessages([]);
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (err) {
      setError(err.message || 'Failed to send message. Please try again later.');
      console.error('Error sending message:', err);
      // Remove the last message on error
      setLocalMessages(prev => prev.slice(0, -1));
    } finally {
      setIsLoading(false);
    }
  };

  const fetchConversations = async () => {
    try {
      const response = await fetch('/api/conversations');
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to fetch conversations');
      }
      const data = await response.json();
      // Handle both response formats (with status wrapper or direct array)
      setConversations(Array.isArray(data) ? data : (data.conversations || []));
    } catch (err) {
      console.error("Error fetching conversations:", err);
      setError(err.message || 'Failed to fetch conversations');
      setConversations([]);
    }
  };

  const loadConversation = async (conversationId) => {
    try {
      const response = await fetch(`/api/conversations/${conversationId}`);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to fetch conversation');
      }
      const data = await response.json();
      if (data.id === conversationId) {
        setCurrentConversationId(conversationId);
      } else {
        throw new Error('Invalid conversation data received');
      }
    } catch (err) {
      console.error("Error loading conversation:", err);
      setError(err.message || 'Failed to load conversation');
      setCurrentConversationId(null);
    }
  };

  const deleteConversation = async (conversationId) => {
    try {
      const response = await fetch(`/api/conversations/${conversationId}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to delete conversation');
      
      if (conversationId === currentConversationId) {
        setCurrentConversationId(null);
      }
      await fetchConversations();
    } catch (err) {
      setError('Failed to delete conversation. Please try again later.');
      console.error('Error deleting conversation:', err);
    }
  };

  const deleteAllConversations = async () => {
    if (!window.confirm('Are you sure you want to delete all conversations?')) return;

    try {
      const response = await fetch('/api/conversations', {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to delete all conversations');
      
      setCurrentConversationId(null);
      await fetchConversations();
    } catch (err) {
      setError('Failed to delete all conversations. Please try again later.');
      console.error('Error deleting all conversations:', err);
    }
  };

  const handleDeleteClick = (conversationId) => {
    const dontShowAgain = localStorage.getItem('dontShowDeleteConfirm') === 'true';
    if (dontShowAgain) {
      deleteConversation(conversationId);
    } else {
      setDeleteConfirmConfig({
        show: true,
        conversationId,
        dontShowAgain: false
      });
    }
  };

  const handleDeleteConfirm = () => {
    if (deleteConfirmConfig.dontShowAgain) {
      localStorage.setItem('dontShowDeleteConfirm', 'true');
    }
    deleteConversation(deleteConfirmConfig.conversationId);
    setDeleteConfirmConfig({ show: false, conversationId: null, dontShowAgain: false });
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmConfig({ show: false, conversationId: null, dontShowAgain: false });
  };

  const currentConversation = conversations.find(
    (conv) => conv.id === currentConversationId
  ) || { messages: [] };

  // Combine conversation messages with local messages
  const displayMessages = [
    ...(currentConversationId ? currentConversation.messages : []),
    ...localMessages
  ];

  return (
    <div className="app-container">
      <ConversationList
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={loadConversation}
        onDeleteConversation={handleDeleteClick}
        onDeleteAllConversations={deleteAllConversations}
        setShowDeleteConfirm={setShowDeleteConfirm}
      />

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

      {deleteConfirmConfig.show && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>Delete Conversation</h3>
            <p>Are you sure you want to delete this conversation? This action cannot be undone.</p>
            <div className="modal-checkbox">
              <input
                type="checkbox"
                id="dontShowAgain"
                checked={deleteConfirmConfig.dontShowAgain}
                onChange={(e) => setDeleteConfirmConfig(prev => ({
                  ...prev,
                  dontShowAgain: e.target.checked
                }))}
              />
              <label htmlFor="dontShowAgain">Don't show this message again</label>
            </div>
            <div className="modal-actions">
              <button onClick={handleDeleteConfirm} className="confirm-btn">
                Delete
              </button>
              <button onClick={handleDeleteCancel} className="cancel-btn">
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
          {!currentConversationId && displayMessages.length === 0 ? (
            <div className="empty-state">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <p>Start a conversation with the AI Assistant</p>
            </div>
          ) : (
            <>
              {displayMessages.map((message, index) => (
                <div 
                  key={`${message.role}-${index}-${message.timestamp}`}
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
              ))}
              {isLoading && (
                <div className="message ai-message loading-message">
                  <div className="message-avatar">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div className="message-content loading-content">
                    <div className="loading-indicator">
                      <div className="dot"></div>
                      <div className="dot"></div>
                      <div className="dot"></div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="chat-input-form">
          <div className="input-wrapper">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={handleInputChange}
              placeholder={isLoading ? "Waiting for response..." : "Type your message..."}
              disabled={isLoading}
              autoFocus
              className={isLoading ? "disabled" : ""}
            />
            {isLoading && (
              <div className="input-loading-overlay">
                <div className="loading-indicator">
                  <div className="dot"></div>
                  <div className="dot"></div>
                  <div className="dot"></div>
                </div>
              </div>
            )}
          </div>
          <button 
            type="submit" 
            disabled={isLoading || input.trim() === ''}
            className={isLoading ? "disabled" : ""}
            title={isLoading ? "Please wait for the response" : "Send message"}
          >
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