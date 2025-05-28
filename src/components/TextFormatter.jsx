import React from 'react';

export const formatText = (text) => {
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
    return Math.floor(spaces / 2);
  };

  const processLinks = (text) => {
    return text.replace(/\[(.*?)\]\((.*?)\)/g, (match, text, url) => {
      return `<a href="${url}" target="_blank" rel="noopener noreferrer">${text}</a>`;
    });
  };

  const processBoldText = (text) => {
    text = processLinks(text);
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i}>{part.slice(2, -2)}</strong>;
      }
      if (part.includes('<a href=')) {
        return <span key={i} dangerouslySetInnerHTML={{ __html: part }} />;
      }
      return part;
    });
  };

  lines.forEach((line, index) => {
    const trimmedLine = line.trim();
    const indentLevel = getIndentLevel(line);

    if (!trimmedLine) {
      processList();
      processNumberedList();
      return;
    }

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

    if (trimmedLine.startsWith('* ')) {
      processNumberedList();
      const content = trimmedLine.replace(/^\*\s+/, '');
      
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

    if (/^\d+\.\s/.test(trimmedLine)) {
      processList();
      const match = trimmedLine.match(/^(\d+)\.\s+(.*)/);
      if (match) {
        const [, number, content] = match;
        
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

    processList();
    processNumberedList();
    formattedElements.push(
      <div key={index} className="paragraph-section" style={{ marginLeft: `${indentLevel * 20}px` }}>
        <p>{trimmedLine}</p>
      </div>
    );
  });

  processList();
  processNumberedList();

  return formattedElements;
};

export const formatInlineText = (text) => {
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
  return text;
}; 