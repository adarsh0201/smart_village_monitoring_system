import React from 'react';

function Header({ backendStatus, isConnected, onRefresh, isLoading }) {
  return (
    <header className="dashboard-header">
      <div className="header-brand">
        <div className="brand-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 11a9 9 0 0 1 9 9"></path>
            <path d="M4 4a16 16 0 0 1 16 16"></path>
            <circle cx="5" cy="19" r="1"></circle>
          </svg>
        </div>
        <div>
          <h1 className="header-title">Smart Village Monitor</h1>
          <p className="header-subtitle">Satellite Data-Based Smart Village Monitoring System</p>
        </div>
      </div>

      <div className="header-actions">
        <div className={`status-pill ${isConnected ? 'status-online' : 'status-offline'}`}>
          <span className="status-indicator-dot"></span>
          <span className="status-label">
            {isConnected
              ? `Backend: ${backendStatus?.backend || 'DRF'} (${backendStatus?.status || 'Online'})`
              : 'Backend: Disconnected'}
          </span>
        </div>

        <button
          type="button"
          className="btn-refresh"
          onClick={onRefresh}
          disabled={isLoading}
          title="Refresh Data from Backend"
        >
          <svg className={isLoading ? 'spinning' : ''} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.19"></path>
          </svg>
          {isLoading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
    </header>
  );
}

export default Header;

