import { useState, useRef, useEffect } from 'react';
import './App.css';
import ChatMessage from './components/ChatMessage';
import ConversationList from './components/ConversationList';
import ChatInput from './components/ChatInput';

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
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    fetchConversations();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [conversations]);

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

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          conversation_id: currentConversationId,
        }),
      });

      if (!response.ok) throw new Error('Failed to send message');
      
      const data = await response.json();
      setCurrentConversationId(data.conversation_id);
      await fetchConversations();
    } catch (err) {
      setError('Failed to send message. Please try again later.');
      console.error('Error sending message:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchConversations = async () => {
    try {
      const response = await fetch('/api/conversations');
      if (!response.ok) throw new Error('Failed to fetch conversations');
      const data = await response.json();
      setConversations(data.conversations || []);
    } catch (err) {
      setError('Failed to load conversations. Please try again later.');
      console.error('Error fetching conversations:', err);
    }
  };

  const loadConversation = async (conversationId) => {
    try {
      const response = await fetch(`/api/conversations/${conversationId}`);
      if (!response.ok) throw new Error('Failed to fetch conversation');
      const data = await response.json();
      setCurrentConversationId(conversationId);
    } catch (err) {
      setError('Failed to load conversation. Please try again later.');
      console.error('Error loading conversation:', err);
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
          {!currentConversationId || currentConversation.messages.length === 0 ? (
            <div className="empty-state">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              <p>Start a conversation with the AI Assistant</p>
            </div>
          ) : (
            currentConversation.messages.map((message, index) => (
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