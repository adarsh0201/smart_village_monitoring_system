import React from 'react';

function StatsOverview({ backendStatus, villageCount, studyState = 'Rajasthan', isConnected }) {
  return (
    <div className="stats-grid">
      <div className="stat-card">
        <div className="stat-icon-wrapper green-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
            <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
            <line x1="6" y1="6" x2="6.01" y2="6"></line>
            <line x1="6" y1="18" x2="6.01" y2="18"></line>
          </svg>
        </div>
        <div className="stat-content">
          <span className="stat-label">Backend Connection</span>
          <h3 className="stat-value">
            {isConnected ? (backendStatus?.status || 'Connected') : 'Disconnected'}
          </h3>
          <span className="stat-subtext">
            {backendStatus?.backend ? `${backendStatus.backend}` : 'Django REST Framework'}
          </span>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon-wrapper emerald-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
            <circle cx="12" cy="10" r="3"></circle>
          </svg>
        </div>
        <div className="stat-content">
          <span className="stat-label">Study State</span>
          <h3 className="stat-value">{studyState}</h3>
          <span className="stat-subtext">Pilot Focus Region (India)</span>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon-wrapper forest-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
            <polyline points="9 22 9 12 15 12 15 22"></polyline>
          </svg>
        </div>
        <div className="stat-content">
          <span className="stat-label">Total Villages Monitored</span>
          <h3 className="stat-value">{villageCount}</h3>
          <span className="stat-subtext">Active Monitoring Units</span>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon-wrapper sage-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="2" y1="12" x2="22" y2="12"></line>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
          </svg>
        </div>
        <div className="stat-content">
          <span className="stat-label">Data Pipeline</span>
          <h3 className="stat-value">Live API</h3>
          <span className="stat-subtext">Django REST &bull; http://127.0.0.1:8000</span>
        </div>
      </div>
    </div>
  );
}

export default StatsOverview;

