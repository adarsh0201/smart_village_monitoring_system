import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  GeoJSON,
  useMap,
  LayersControl,
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix Vite asset URL resolution for default Leaflet icons
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

// Default center and zoom for Rajasthan state
const RAJASTHAN_CENTER = [26.58, 73.84];
const DEFAULT_ZOOM = 7;

/**
 * Creates modern SVG-based DivIcons styled for the Smart Village dashboard.
 */
function createVillagePinIcon(isSelected = false) {
  const pinColor = isSelected ? '#ffb300' : '#2e7d32';
  const strokeColor = isSelected ? '#d97706' : '#1b5e20';
  const size = isSelected ? 38 : 30;
  const dotColor = isSelected ? '#b45309' : '#a5d6a7';

  const svgHtml = `
    <div style="position: relative; width: ${size}px; height: ${size + 8}px; display: flex; align-items: center; justify-content: center;">
      <svg width="${size}" height="${size + 8}" viewBox="0 0 32 40" fill="none" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 3px 5px rgba(0,0,0,0.35)); transition: transform 0.2s ease;">
        <path d="M16 0C7.16344 0 0 7.16344 0 16C0 26.5 16 40 16 40C16 40 32 26.5 32 16C32 7.16344 24.8366 0 16 0Z" fill="${pinColor}" stroke="${strokeColor}" stroke-width="2"/>
        <circle cx="16" cy="15" r="6" fill="#ffffff"/>
        <circle cx="16" cy="15" r="3.5" fill="${dotColor}"/>
      </svg>
      ${isSelected ? '<span style="position: absolute; bottom: -2px; width: 10px; height: 10px; border-radius: 50%; background: #ffb300; opacity: 0.6; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></span>' : ''}
    </div>
  `;

  return L.divIcon({
    className: 'custom-gis-pin',
    html: svgHtml,
    iconSize: [size, size + 8],
    iconAnchor: [size / 2, size + 8],
    popupAnchor: [0, -(size + 4)],
  });
}

/**
 * Controller subcomponent to handle dynamic panning/zooming.
 */
function MapController({ targetCoords, resetTrigger }) {
  const map = useMap();

  useEffect(() => {
    if (targetCoords && targetCoords.length === 2) {
      map.flyTo(targetCoords, 11, { duration: 1.2, easeLinearity: 0.25 });
    }
  }, [targetCoords, map]);

  useEffect(() => {
    if (resetTrigger > 0) {
      map.flyTo(RAJASTHAN_CENTER, DEFAULT_ZOOM, { duration: 1.0 });
    }
  }, [resetTrigger, map]);

  return null;
}

function VillageMap({
  villages = [],
  isLoading = false,
  error = null,
  selectedVillage = null,
  onSelectVillage = () => {},
  onRefresh = () => {},
}) {
  const [resetCount, setResetCount] = useState(0);
  const markerRefs = useRef({});

  const activeVillage = selectedVillage;

  // Extract target coordinates for camera flyTo
  const targetCoordinates = useMemo(() => {
    if (!activeVillage) return null;
    if (activeVillage.latitude && activeVillage.longitude) {
      return [activeVillage.latitude, activeVillage.longitude];
    }
    if (activeVillage.location?.coordinates?.length === 2) {
      return [activeVillage.location.coordinates[1], activeVillage.location.coordinates[0]];
    }
    return null;
  }, [activeVillage]);

  // Filter valid villages with geographic coordinates
  const validVillages = useMemo(() => {
    return villages.filter((v) => {
      const lat = v.latitude ?? v.location?.coordinates?.[1];
      const lng = v.longitude ?? v.location?.coordinates?.[0];
      return (
        typeof lat === 'number' &&
        typeof lng === 'number' &&
        !isNaN(lat) &&
        !isNaN(lng) &&
        lat >= -90 &&
        lat <= 90 &&
        lng >= -180 &&
        lng <= 180
      );
    });
  }, [villages]);

  const handleVillageClick = (village) => {
    onSelectVillage(village);
  };

  const handleResetView = () => {
    setResetCount((prev) => prev + 1);
    onSelectVillage(null);
  };

  return (
    <section className="village-map-section">
      <div className="section-header">
        <div>
          <h2 className="section-title">Geographical Distribution of Monitored Villages</h2>
          <p className="section-subtitle">
            Interactive GIS spatial mapping layer powered by PostGIS and OpenStreetMap / Satellite base layers
          </p>
        </div>

        <div className="map-actions-bar">
          <span className="badge-count">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
              <circle cx="12" cy="10" r="3"></circle>
            </svg>
            {validVillages.length} Villages Plotted
          </span>

          <button
            type="button"
            className="btn-map-control"
            onClick={handleResetView}
            title="Reset map view to Rajasthan state"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
              <path d="M3 3v5h5"></path>
            </svg>
            Reset View
          </button>
        </div>
      </div>

      {/* Main Map + Selected Inspector Layout */}
      <div className="map-layout-grid">
        {/* Left / Main Map Canvas */}
        <div className="map-canvas-wrapper">
          {isLoading && (
            <div className="map-loading-overlay">
              <div className="spinner"></div>
              <span>Loading GIS spatial points from Django REST API...</span>
            </div>
          )}

          {error && !isLoading && (
            <div className="map-error-overlay">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#c62828" strokeWidth="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
              <h4>Unable to load GIS village map</h4>
              <p>{error}</p>
              <button type="button" className="btn-retry-map" onClick={onRefresh}>
                Retry Fetching Data
              </button>
            </div>
          )}

          <MapContainer
            center={RAJASTHAN_CENTER}
            zoom={DEFAULT_ZOOM}
            scrollWheelZoom={true}
            className="leaflet-map-container"
          >
            <MapController targetCoords={targetCoordinates} resetTrigger={resetCount} />

            <LayersControl position="topright">
              <LayersControl.BaseLayer checked name="OpenStreetMap Standard">
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  maxZoom={19}
                />
              </LayersControl.BaseLayer>

              <LayersControl.BaseLayer name="Esri World Imagery (Satellite)">
                <TileLayer
                  attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
                  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                  maxZoom={18}
                />
              </LayersControl.BaseLayer>

              <LayersControl.BaseLayer name="CartoDB Positron (Clean Light)">
                <TileLayer
                  attribution='&copy; <a href="https://carto.com/attributions" target="_blank" rel="noreferrer">CARTO</a>'
                  url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                  maxZoom={19}
                />
              </LayersControl.BaseLayer>
            </LayersControl>

            {/* Village GeoJSON Boundaries (when available) */}
            {validVillages.map((village) => {
              if (!village.boundary) return null;
              const isSelected = activeVillage?.id === village.id;
              return (
                <GeoJSON
                  key={`boundary-${village.id}-${village.updated_at || ''}-${isSelected ? 'sel' : 'norm'}`}
                  data={village.boundary}
                  style={{
                    color: isSelected ? '#b45309' : '#1b5e20',
                    weight: isSelected ? 3 : 2,
                    fillColor: isSelected ? '#ffb300' : '#2e7d32',
                    fillOpacity: isSelected ? 0.45 : 0.25,
                    dashArray: isSelected ? '' : '4, 4',
                  }}
                  eventHandlers={{
                    click: () => handleVillageClick(village),
                  }}
                />
              );
            })}

            {/* Village Point Markers */}
            {validVillages.map((village) => {
              const lat = village.latitude ?? village.location?.coordinates?.[1];
              const lng = village.longitude ?? village.location?.coordinates?.[0];
              const isSelected = activeVillage?.id === village.id;

              return (
                <Marker
                  key={`marker-${village.id}`}
                  position={[lat, lng]}
                  icon={createVillagePinIcon(isSelected)}
                  eventHandlers={{
                    click: () => handleVillageClick(village),
                  }}
                  ref={(ref) => {
                    if (ref) {
                      markerRefs.current[village.id] = ref;
                    }
                  }}
                >
                  <Popup className="village-popup">
                    <div className="popup-card">
                      <div className="popup-badge-row">
                        <span className="popup-state-badge">{village.state || 'Rajasthan'}</span>
                        <span className="popup-id-badge">#{village.id}</span>
                      </div>
                      <h3 className="popup-title">{village.name}</h3>
                      <p className="popup-district">
                        <strong>District:</strong> {village.district}
                      </p>

                      <div className="popup-meta-grid">
                        <div className="popup-meta-item">
                          <span className="popup-meta-label">Latitude</span>
                          <span className="popup-meta-value">{lat.toFixed(4)}° N</span>
                        </div>
                        <div className="popup-meta-item">
                          <span className="popup-meta-label">Longitude</span>
                          <span className="popup-meta-value">{lng.toFixed(4)}° E</span>
                        </div>
                        <div className="popup-meta-item">
                          <span className="popup-meta-label">Area (ha)</span>
                          <span className="popup-meta-value">
                            {village.area_hectares != null ? `${village.area_hectares} ha` : 'Pending'}
                          </span>
                        </div>
                        <div className="popup-meta-item">
                          <span className="popup-meta-label">Population</span>
                          <span className="popup-meta-value">
                            {village.population != null ? village.population.toLocaleString() : 'N/A'}
                          </span>
                        </div>
                      </div>

                      <div className="popup-status-note">
                        <span
                          className={`boundary-indicator-dot ${
                            village.boundary ? 'has-boundary' : 'no-boundary'
                          }`}
                        ></span>
                        <span>
                          {village.boundary
                            ? 'Boundary polygon loaded'
                            : 'Centroid point marker (Boundary pending satellite ingestion)'}
                        </span>
                      </div>

                      <button
                        type="button"
                        className="btn-popup-select"
                        onClick={() => handleVillageClick(village)}
                      >
                        Inspect Village
                      </button>
                    </div>
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>

          {/* Map Legend */}
          <div className="map-legend">
            <span className="legend-title">GIS Map Legend</span>
            <div className="legend-items">
              <div className="legend-item">
                <span className="legend-pin green"></span>
                <span>Monitored Village</span>
              </div>
              <div className="legend-item">
                <span className="legend-pin amber"></span>
                <span>Selected Village</span>
              </div>
              <div className="legend-item">
                <span className="legend-polygon"></span>
                <span>Boundary GeoJSON</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right / Selected Village Inspector Panel */}
        <div className="village-inspector-panel">
          <div className="inspector-header">
            <div className="inspector-title-row">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
              </svg>
              <h3>Spatial Village Inspector</h3>
            </div>
            {activeVillage && (
              <button
                type="button"
                className="btn-clear-selection"
                onClick={() => {
                  onSelectVillage(null);
                }}
              >
                Clear
              </button>
            )}
          </div>

          {activeVillage ? (
            <div className="inspector-body">
              <div className="inspector-hero-card">
                <div className="inspector-chip-row">
                  <span className="chip-state">{activeVillage.state || 'Rajasthan'}</span>
                  <span className="chip-active">Unit #{activeVillage.id}</span>
                </div>
                <h4 className="inspector-name">{activeVillage.name}</h4>
                <p className="inspector-sub">
                  District: <strong>{activeVillage.district}</strong>
                </p>
              </div>

              <div className="inspector-specs-table">
                <div className="spec-row">
                  <span className="spec-label">Latitude</span>
                  <span className="spec-value">
                    {(activeVillage.latitude ?? activeVillage.location?.coordinates?.[1])?.toFixed(6)}° N
                  </span>
                </div>
                <div className="spec-row">
                  <span className="spec-label">Longitude</span>
                  <span className="spec-value">
                    {(activeVillage.longitude ?? activeVillage.location?.coordinates?.[0])?.toFixed(6)}° E
                  </span>
                </div>
                <div className="spec-row">
                  <span className="spec-label">Spatial SRID</span>
                  <span className="spec-value code-pill">EPSG:4326 (WGS 84)</span>
                </div>
                <div className="spec-row">
                  <span className="spec-label">Area (Hectares)</span>
                  <span className="spec-value">
                    {activeVillage.area_hectares != null
                      ? `${activeVillage.area_hectares} ha`
                      : 'Pending GIS Calc'}
                  </span>
                </div>
                <div className="spec-row">
                  <span className="spec-label">Census Population</span>
                  <span className="spec-value">
                    {activeVillage.population != null
                      ? activeVillage.population.toLocaleString()
                      : 'Uninhabited / N/A'}
                  </span>
                </div>
                <div className="spec-row">
                  <span className="spec-label">Boundary Data</span>
                  <span
                    className={`spec-value ${
                      activeVillage.boundary ? 'status-text-green' : 'status-text-amber'
                    }`}
                  >
                    {activeVillage.boundary
                      ? 'Available (MultiPolygon)'
                      : 'Centroid Point (Boundary Pending)'}
                  </span>
                </div>
              </div>

              <div className="inspector-actions">
                <button
                  type="button"
                  className="btn-zoom-target"
                  onClick={() => {
                    const lat = activeVillage.latitude ?? activeVillage.location?.coordinates?.[1];
                    const lng = activeVillage.longitude ?? activeVillage.location?.coordinates?.[0];
                    if (lat && lng) {
                      onSelectVillage({ ...activeVillage });
                    }
                  }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    <line x1="11" y1="8" x2="11" y2="14"></line>
                    <line x1="8" y1="11" x2="14" y2="11"></line>
                  </svg>
                  Center on Map
                </button>
              </div>
            </div>
          ) : (
            <div className="inspector-empty-state">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <p>Click any village marker or boundary polygon on the map to inspect geographic coordinates and attributes.</p>
            </div>
          )}

          {/* Quick Village Navigator List */}
          <div className="village-quick-list">
            <span className="quick-list-title">Plotted Villages Directory ({validVillages.length})</span>
            <div className="quick-list-items">
              {validVillages.map((v) => (
                <button
                  key={`quick-${v.id}`}
                  type="button"
                  className={`btn-quick-village ${activeVillage?.id === v.id ? 'active' : ''}`}
                  onClick={() => handleVillageClick(v)}
                >
                  <span className="quick-village-name">{v.name}</span>
                  <span className="quick-village-dist">{v.district}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default VillageMap;
