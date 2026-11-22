import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

function ErrorState({ title = "System Error", message, onRetry }) {
  return (
    <div className="card" style={{ backgroundColor: 'var(--color-error-bg)', borderColor: 'var(--color-error-border)', marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
        <div style={{ color: 'var(--color-error)', flexShrink: 0, marginTop: '2px' }}>
          <AlertCircle size={22} />
        </div>
        <div style={{ flex: 1 }}>
          <h4 style={{ margin: '0 0 4px', fontSize: '15px', color: '#991b1b', fontWeight: 700 }}>
            {title}
          </h4>
          <p style={{ margin: '0 0 10px', fontSize: '13px', color: 'var(--color-error)', lineHeight: 1.5 }}>
            {message}
          </p>
          {onRetry && (
            <button
              type="button"
              className="btn btn-sm"
              style={{ backgroundColor: 'var(--color-error)', color: '#ffffff', borderColor: 'var(--color-error)' }}
              onClick={onRetry}
            >
              <RefreshCw size={13} />
              Retry Request
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default ErrorState;

