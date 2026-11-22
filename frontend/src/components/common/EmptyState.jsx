import React from 'react';
import { Database } from 'lucide-react';

function EmptyState({ icon: Icon = Database, title = "No Records Found", message = "There is currently no data matching your criteria.", actionLabel, onAction }) {
  return (
    <div style={{ textAlign: 'center', padding: '48px 20px', background: 'var(--color-surface-muted)', borderRadius: 'var(--radius-lg)', border: '1px dashed var(--color-border-dark)' }}>
      <div style={{ width: '48px', height: '48px', borderRadius: '50%', background: 'var(--color-surface)', border: '1px solid var(--color-border)', color: 'var(--color-text-muted)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: '12px' }}>
        <Icon size={24} />
      </div>
      <h4 style={{ margin: '0 0 6px', fontSize: '15px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
        {title}
      </h4>
      <p style={{ margin: '0 0 16px', fontSize: '13px', color: 'var(--color-text-secondary)', maxWidth: '420px', marginInline: 'auto', lineHeight: 1.5 }}>
        {message}
      </p>
      {actionLabel && onAction && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}

export default EmptyState;

