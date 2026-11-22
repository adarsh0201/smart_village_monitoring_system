import React from 'react';

function LoadingIndicator({ message = 'Loading data from Django REST API...' }) {
  return (
    <div className="loading-container">
      <div className="spinner"></div>
      <p className="loading-text">{message}</p>
    </div>
  );
}

export default LoadingIndicator;

