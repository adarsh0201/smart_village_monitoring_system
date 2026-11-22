import React from 'react';
import {
  MapPin,
  ChevronRight,
  ChevronLeft,
  Satellite,
  Focus,
  Info,
} from 'lucide-react';

function SpatialInspector({
  selectedVillage,
  onClearSelection,
  onNavigateToSatellite,
  onCenterOnVillage,
  isCollapsed,
  onToggleCollapse,
  validVillages = [],
  onSelectVillage = () => {},
}) {
  if (isCollapsed) {
    return (
      <div style={{ position: 'absolute', top: '16px', right: '16px', zIndex: 850 }}>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          style={{ background: '#ffffff', boxShadow: 'var(--shadow-md)' }}
          onClick={onToggleCollapse}
          title="Open Village Spatial Inspector"
        >
          <ChevronLeft size={15} />
          <span>Inspector</span>
          {selectedVillage && <span className="badge badge-green" style={{ marginLeft: '4px' }}>#{selectedVillage.id}</span>}
        </button>
      </div>
    );
  }

  return (
    <div className="village-inspector-panel" style={{ height: '100%', overflowY: 'auto' }}>
      <div className="inspector-header">
        <div className="inspector-title-row">
          <MapPin size={17} />
          <h3>Spatial Inspector</h3>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {selectedVillage && (
            <button
              type="button"
              className="btn-clear-selection"
              onClick={onClearSelection}
              title="Clear selection"
            >
              Clear
            </button>
          )}
          <button
            type="button"
            className="btn-clear-selection"
            onClick={onToggleCollapse}
            title="Minimize inspector panel"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>

      {selectedVillage ? (
        <div className="inspector-body">
          <div className="inspector-hero-card">
            <div className="inspector-chip-row">
              <span className="chip-state">{selectedVillage.state || 'Rajasthan'}</span>
              <span className="chip-active">Monitoring Unit #{selectedVillage.id}</span>
            </div>
            <h4 className="inspector-name">{selectedVillage.name}</h4>
            <p className="inspector-sub">
              District: <strong>{selectedVillage.district}</strong>
            </p>
          </div>

          <div className="inspector-specs-table">
            <div className="spec-row">
              <span className="spec-label">Latitude</span>
              <span className="spec-value">
                {(selectedVillage.latitude ?? selectedVillage.location?.coordinates?.[1])?.toFixed(6)}° N
              </span>
            </div>
            <div className="spec-row">
              <span className="spec-label">Longitude</span>
              <span className="spec-value">
                {(selectedVillage.longitude ?? selectedVillage.location?.coordinates?.[0])?.toFixed(6)}° E
              </span>
            </div>
            <div className="spec-row">
              <span className="spec-label">Coordinate SRID</span>
              <span className="spec-value code-pill">EPSG:4326 (WGS 84)</span>
            </div>
            <div className="spec-row">
              <span className="spec-label">Area (Hectares)</span>
              <span className="spec-value">
                {selectedVillage.area_hectares != null
                  ? `${selectedVillage.area_hectares} ha`
                  : 'Pending GIS Calc'}
              </span>
            </div>
            <div className="spec-row">
              <span className="spec-label">Census Population</span>
              <span className="spec-value">
                {selectedVillage.population != null
                  ? selectedVillage.population.toLocaleString()
                  : 'Uninhabited / N/A'}
              </span>
            </div>
            <div className="spec-row">
              <span className="spec-label">Boundary Layer</span>
              <span
                className={`spec-value ${
                  selectedVillage.boundary ? 'status-text-green' : 'status-text-amber'
                }`}
              >
                {selectedVillage.boundary
                  ? 'Official Polygon'
                  : 'Centroid (Boundary Pending)'}
              </span>
            </div>
          </div>

          <div className="inspector-actions" style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '12px' }}>
            <button
              type="button"
              className="btn-zoom-target"
              onClick={onCenterOnVillage}
            >
              <Focus size={14} />
              Center Camera on Village
            </button>

            {onNavigateToSatellite && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => onNavigateToSatellite(selectedVillage)}
              >
                <Satellite size={14} />
                Acquire Satellite Imagery
              </button>
            )}
          </div>
        </div>
      ) : (
        <div className="inspector-empty-state">
          <Info size={32} style={{ color: 'var(--color-text-muted)' }} />
          <p>
            Click any village marker or boundary on the map to inspect geographic coordinates and spatial properties.
          </p>
        </div>
      )}

      {/* Quick Village Directory */}
      <div className="village-quick-list" style={{ marginTop: 'auto' }}>
        <span className="quick-list-title">Plotted Villages Directory ({validVillages.length})</span>
        <div className="quick-list-items">
          {validVillages.map((v) => (
            <button
              key={`quick-${v.id}`}
              type="button"
              className={`btn-quick-village ${selectedVillage?.id === v.id ? 'active' : ''}`}
              onClick={() => onSelectVillage(v)}
            >
              <span className="quick-village-name">{v.name}</span>
              <span className="quick-village-dist">{v.district}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default SpatialInspector;
