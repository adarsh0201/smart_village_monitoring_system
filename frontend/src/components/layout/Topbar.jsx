import React from 'react';
import { Menu, RefreshCw, MapPin, CheckCircle2, AlertTriangle } from 'lucide-react';

const PAGE_TITLES = {
  overview: 'Overview Dashboard',
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
          aria-label="Open mobile navigation"
        >
          <Menu size={20} />
        </button>

        <nav className="topbar-breadcrumbs" aria-label="Breadcrumb">
          <span className="breadcrumb-root">Rajasthan</span>
          <span className="breadcrumb-separator">/</span>
          <span className="breadcrumb-active">{currentTitle}</span>
        </nav>
      </div>

      <div className="topbar-right">
        {/* Selected Village Quick Selector */}
        {villages.length > 0 && (
          <div className="topbar-village-selector-wrapper">
            <label htmlFor="topbar-village-select" style={{ display: 'none' }}>
              Select Active Village
            </label>
            <div className="topbar-village-badge">
              <MapPin size={13} />
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
                  color: 'inherit',
                  fontWeight: 600,
                  fontSize: '12px',
                  cursor: 'pointer',
                  outline: 'none',
                }}
              >
                <option value="" style={{ color: '#0f172a' }}>
                  -- Select Monitored Village --
                </option>
                {villages.map((v) => (
                  <option key={v.id} value={v.id} style={{ color: '#0f172a' }}>
                    {v.name} ({v.district})
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* Backend Status Pill */}
        <div className={`topbar-status-indicator ${isConnected ? 'online' : 'offline'}`}>
          {isConnected ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
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
          <RefreshCw size={13} className={isLoading ? 'spinning' : ''} />
          <span>Sync</span>
        </button>
      </div>
    </header>
  );
}

export default Topbar;

