import React, { useState, useMemo, useRef, useEffect } from 'react';
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
import { RotateCcw, MapPin, Layers } from 'lucide-react';

import SpatialInspector from './SpatialInspector';

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

const RAJASTHAN_CENTER = [26.58, 73.84];
const DEFAULT_ZOOM = 7;

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

function MapController({ targetCoords, resetTrigger, layoutTrigger }) {
  const map = useMap();

  // Invalidate map dimensions on mount and layout shifts
  useEffect(() => {
    map.invalidateSize();
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 200);
    return () => clearTimeout(timer);
  }, [map, layoutTrigger]);

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
  onNavigateToSatellite = null,
  onRefresh = () => {},
}) {
  const [resetCount, setResetCount] = useState(0);
  const [isInspectorCollapsed, setIsInspectorCollapsed] = useState(false);
  const markerRefs = useRef({});

  const activeVillage = selectedVillage;

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

  const handleResetView = () => {
    setResetCount((prev) => prev + 1);
    onSelectVillage(null);
  };

  return (
    <div className="gis-explorer-workspace">
      {/* Workspace Header */}
      <div className="page-header">
        <div className="page-header-title-block">
          <h1 className="page-title">GIS Spatial Explorer</h1>
          <p className="page-subtitle">
            PostGIS spatial vector layers with multi-provider satellite basemaps &bull; EPSG:4326 WGS 84
          </p>
        </div>

        <div className="page-header-actions">
          <span className="badge badge-green" style={{ padding: '6px 12px', fontSize: '12px' }}>
            <MapPin size={13} />
            {validVillages.length} Villages Mapped
          </span>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleResetView}
            title="Reset map camera to Rajasthan state overview"
          >
            <RotateCcw size={13} />
            Reset Camera
          </button>
        </div>
      </div>

      {/* Main Map + Inspector Layout */}
      <div
        className="map-layout-grid"
        style={{
          gridTemplateColumns: isInspectorCollapsed ? '1fr' : '1fr 340px',
        }}
      >
        {/* Map Canvas Wrapper */}
        <div className="map-canvas-wrapper">
          {isLoading && (
            <div className="map-loading-overlay">
              <div className="spinner"></div>
              <span>Connecting and fetching spatial geometries from PostGIS...</span>
            </div>
          )}

          {error && !isLoading && (
            <div className="map-error-overlay">
              <h4>GIS Connection Error</h4>
              <p>{error}</p>
              <button type="button" className="btn btn-primary btn-sm" onClick={onRefresh}>
                Retry Loading
              </button>
            </div>
          )}

          <MapContainer
            center={RAJASTHAN_CENTER}
            zoom={DEFAULT_ZOOM}
            maxZoom={22}
            scrollWheelZoom={true}
            className="leaflet-map-container"
          >
            <MapController
              targetCoords={targetCoordinates}
              resetTrigger={resetCount}
              layoutTrigger={isInspectorCollapsed}
            />

            <LayersControl position="topright">
              <LayersControl.BaseLayer checked name="OpenStreetMap Standard">
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  maxNativeZoom={19}
                  maxZoom={22}
                />
              </LayersControl.BaseLayer>

              <LayersControl.BaseLayer name="Esri World Imagery (Satellite)">
                <TileLayer
                  attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
                  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                  maxNativeZoom={18}
                  maxZoom={22}
                />
              </LayersControl.BaseLayer>

              <LayersControl.BaseLayer name="CartoDB Positron (Clean Light)">
                <TileLayer
                  attribution='&copy; <a href="https://carto.com/attributions" target="_blank" rel="noreferrer">CARTO</a>'
                  url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                  maxNativeZoom={19}
                  maxZoom={22}
                />
              </LayersControl.BaseLayer>
            </LayersControl>

            {/* Official Boundaries (when available) */}
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
                    click: () => onSelectVillage(village),
                  }}
                />
              );
            })}

            {/* Point Markers */}
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
                    click: () => onSelectVillage(village),
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
                            ? 'Official boundary loaded'
                            : 'Centroid point (Boundary pending satellite ingestion)'}
                        </span>
                      </div>

                      <button
                        type="button"
                        className="btn-popup-select"
                        onClick={() => onSelectVillage(village)}
                      >
                        Inspect Spatial Unit
                      </button>
                    </div>
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>

          {/* Floating Map Legend */}
          <div className="map-legend">
            <span className="legend-title">
              <Layers size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: 'middle' }} />
              Symbology Legend
            </span>
            <div className="legend-items">
              <div className="legend-item">
                <span className="legend-pin green"></span>
                <span>Monitored Village Centroid</span>
              </div>
              <div className="legend-item">
                <span className="legend-pin amber"></span>
                <span>Active Selected Unit</span>
              </div>
              <div className="legend-item">
                <span className="legend-polygon"></span>
                <span>PostGIS MultiPolygon Boundary</span>
              </div>
            </div>
          </div>
        </div>

        {/* Spatial Inspector Panel */}
        <SpatialInspector
          selectedVillage={activeVillage}
          onClearSelection={() => onSelectVillage(null)}
          onNavigateToSatellite={onNavigateToSatellite}
          onCenterOnVillage={() => {
            if (activeVillage) {
              onSelectVillage({ ...activeVillage });
            }
          }}
          isCollapsed={isInspectorCollapsed}
          onToggleCollapse={() => setIsInspectorCollapsed(!isInspectorCollapsed)}
          validVillages={validVillages}
          onSelectVillage={onSelectVillage}
        />
      </div>
    </div>
  );
}

export default VillageMap;