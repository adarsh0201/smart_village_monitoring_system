import React from 'react';

function ErrorBanner({ message, onRetry }) {
  return (
    <div className="error-banner">
      <div className="error-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
      </div>
      <div className="error-content">
        <h4>Connection Error</h4>
        <p>{message || 'Unable to communicate with the Django REST Framework backend.'}</p>
        <span className="error-help">
          Make sure your Django server is running at <code>http://127.0.0.1:8000</code>.
        </span>
      </div>
      {onRetry && (
        <button type="button" className="btn-retry" onClick={onRetry}>
          Retry Connection
        </button>
      )}
    </div>
  );
}

export default ErrorBanner;

