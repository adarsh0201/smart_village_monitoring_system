import React from 'react';

function Loading({ message = "Loading geospatial data from Django backend..." }) {
  return (
    <div className="card" style={{ padding: '60px 20px', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
      <div className="spinner" style={{ marginBottom: '16px' }}></div>
      <p style={{ margin: 0, fontSize: '14px', color: 'var(--color-text-secondary)', fontWeight: 500 }}>
        {message}
      </p>
    </div>
  );
}

export default Loading;

