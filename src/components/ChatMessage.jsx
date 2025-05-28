import React from 'react';
import { formatText } from './TextFormatter';

const ChatMessage = ({ message, isUser }) => {
  const { role, content, timestamp } = message;
  const formattedTime = timestamp ? new Date(timestamp).toLocaleTimeString() : '';

  return (
    <div className={`chat-message ${isUser ? 'user-message' : 'assistant-message'}`}>
      <div className="message-header">
        <span className="message-role">{role === 'user' ? 'You' : 'Assistant'}</span>
        {formattedTime && <span className="message-time">{formattedTime}</span>}
      </div>
      <div className="message-content">
        {formatText(content)}
      </div>
    </div>
  );
};

export default ChatMessage; 