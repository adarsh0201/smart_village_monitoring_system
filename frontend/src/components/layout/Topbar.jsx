import React from 'react';
import { Menu, RefreshCw, MapPin, CheckCircle2, AlertTriangle } from 'lucide-react';

const PAGE_TITLES = {
  overview: 'Executive Monitoring Overview',
  gis: 'GIS Explorer & Spatial Mapping',
  villages: 'Village Registry & Administrative Units',
  satellite: 'Sentinel-2 Satellite Imagery Acquisition',
  analytics: 'Environmental & Spectral Analytics',
  change: 'Multi-Temporal Change Detection',
  reports: 'Monitoring Reports & Documentation',
};

function Topbar({
  activePage,
  onOpenMobile,
  isConnected,
  isLoading,
  onRefresh,
  villages = [],
  selectedVillage = null,
  onSelectVillage = () => {},
}) {
  const currentTitle = PAGE_TITLES[activePage] || 'Dashboard';

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          type="button"
          className="btn-mobile-menu"
          onClick={onOpenMobile}
          aria-label="Open navigation menu"
        >
          <Menu size={18} />
          <span>Menu</span>
        </button>

        <nav className="topbar-breadcrumbs" aria-label="Breadcrumb">
          <span className="breadcrumb-root">
            {selectedVillage?.state || 'Smart Village WebGIS'}
          </span>
          <span className="breadcrumb-separator" aria-hidden="true">/</span>
          <span className="breadcrumb-active">{currentTitle}</span>
        </nav>
      </div>

      <div className="topbar-right">
        {/* Selected Village Quick Selector */}
        {villages.length > 0 && (
          <div className="topbar-village-selector-wrapper">
            <div className="topbar-village-badge">
              <MapPin size={15} aria-hidden="true" />
              <label
                htmlFor="topbar-village-select"
                style={{
                  fontSize: '12px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.03em',
                  color: 'var(--color-text-secondary)',
                }}
              >
                Active Village:
              </label>
              <select
                id="topbar-village-select"
                value={selectedVillage?.id || ''}
                onChange={(e) => {
                  const val = e.target.value;
                  const found = villages.find((v) => String(v.id) === String(val)) || null;
                  onSelectVillage(found);
                }}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--color-primary-dark)',
                  fontWeight: 700,
                  fontSize: '13.5px',
                  cursor: 'pointer',
                  outline: 'none',
                }}
              >
                <option value="" style={{ color: '#2C2A29' }}>
                  -- Select Monitored Village --
                </option>
                {villages.map((v) => (
                  <option key={v.id} value={v.id} style={{ color: '#2C2A29' }}>
                    {v.name} ({v.district})
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* Backend Status Pill */}
        <div className={`topbar-status-indicator ${isConnected ? 'online' : 'offline'}`}>
          {isConnected ? (
            <CheckCircle2 size={15} aria-hidden="true" />
          ) : (
            <AlertTriangle size={15} aria-hidden="true" />
          )}
          <span>{isConnected ? 'PostgreSQL Connected' : 'Backend Disconnected'}</span>
        </div>

        {/* Refresh Action */}
        <button
          type="button"
          className="btn-topbar-action"
          onClick={onRefresh}
          disabled={isLoading}
          title="Refresh live data from Django REST API"
        >
          <RefreshCw size={15} className={isLoading ? 'spinning' : ''} aria-hidden="true" />
          <span>{isLoading ? 'Syncing...' : 'Sync Data'}</span>
        </button>
      </div>
    </header>
  );
}

export default Topbar;
