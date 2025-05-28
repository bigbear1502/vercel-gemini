import React from 'react';

const ConversationList = ({ 
  conversations, 
  currentConversationId, 
  onSelectConversation, 
  onDeleteConversation, 
  onDeleteAllConversations,
  setShowDeleteConfirm
}) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>Chat History</h2>
        <div className="sidebar-actions">
          <button 
            onClick={() => onSelectConversation(null)} 
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
              onClick={() => onSelectConversation(conv.id)}
            >
              <h3>{conv.title}</h3>
              <p>{new Date(conv.updated_at).toLocaleDateString()}</p>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDeleteConversation(conv.id);
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
  );
};

export default ConversationList; 