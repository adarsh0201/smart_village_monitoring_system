import React, { useState, useEffect, useCallback } from 'react';
import {
  Sparkles,
  Layers,
  MapPin,
  RefreshCw,
  ExternalLink,
  Sliders,
  AlertCircle,
  Trees,
  Wheat,
  Home,
  Waves,
  Mountain,
  Grid,
} from 'lucide-react';
import {
  MapContainer,
  TileLayer,
  ImageOverlay,
  LayersControl,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { getVillageLulcAnalytics, getVillagePredictedMapUrl } from '../../services/api';

const CLASS_ICONS = {
  10: Trees,
  30: Mountain,
  40: Wheat,
  50: Home,
  60: Grid,
  80: Waves,
};

export function LulcAnalyticsDashboard({
  villageId,
  villageName = 'Village',
  onNavigateToGis = null,
}) {
  const [analyticsState, setAnalyticsState] = useState({ villageId: null, data: null, error: null });
  const [loadedVillageId, setLoadedVillageId] = useState(null);
  const [refreshTick, setRefreshTick] = useState(0);
  const [overlayOpacity, setOverlayOpacity] = useState(85);

  const loading = Boolean(villageId) && loadedVillageId !== `${villageId}:${refreshTick}`;
  const analytics = analyticsState.villageId === `${villageId}:${refreshTick}` ? analyticsState.data : null;
  const error = analyticsState.villageId === `${villageId}:${refreshTick}` ? analyticsState.error : null;

  useEffect(() => {
    if (!villageId) return;
    let isCurrent = true;
    const key = `${villageId}:${refreshTick}`;
    getVillageLulcAnalytics(villageId)
      .then((data) => {
        if (isCurrent) {
          setAnalyticsState({ villageId: key, data, error: null });
          setLoadedVillageId(key);
        }
      })
      .catch((err) => {
        console.error('Failed to load LULC analytics:', err);
        if (isCurrent) {
          setAnalyticsState({
            villageId: key,
            data: null,
            error: err?.response?.data?.error || err.message || 'Failed to fetch analytics',
          });
          setLoadedVillageId(key);
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [villageId, refreshTick]);

  const fetchAnalytics = useCallback(() => {
    setRefreshTick((t) => t + 1);
  }, []);

  if (loading) {
    return (
      <div
        className="card"
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '60px 24px',
          minHeight: '380px',
        }}
      >
        <div className="spinner" style={{ marginBottom: '16px' }}></div>
        <span style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
          Extracting Land Use &amp; Land Cover statistics for {villageName}...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert-banner alert-danger" style={{ margin: '20px 0' }}>
        <AlertCircle size={20} aria-hidden="true" />
        <div style={{ flex: 1 }}>
          <strong>Error loading LULC analytics:</strong> {error}
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={fetchAnalytics}>
          <RefreshCw size={14} aria-hidden="true" />
          <span>Retry Loading</span>
        </button>
      </div>
    );
  }

  if (!analytics || !analytics.available) {
    return (
      <div
        style={{
          background: 'var(--color-surface-muted)',
          border: '1px dashed var(--color-border-dark)',
          borderRadius: 'var(--radius-lg)',
          padding: '44px 24px',
          textAlign: 'center',
          margin: '20px 0',
        }}
      >
        <Sparkles size={36} style={{ color: 'var(--color-primary)', marginBottom: '12px' }} aria-hidden="true" />
        <h3 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: '8px' }}>
          Land Cover Classification Pending for {villageName}
        </h3>
        <p
          style={{
            fontSize: '14.5px',
            color: 'var(--color-text-secondary)',
            maxWidth: '520px',
            margin: '0 auto 18px auto',
            lineHeight: 1.6,
          }}
        >
          The multi-modal Random Forest model has not yet generated a land cover map for this village. Execute the backend pipeline command:
        </p>
        <code
          style={{
            display: 'inline-block',
            background: 'var(--color-surface)',
            color: 'var(--color-text-primary)',
            border: '1px solid var(--color-border-dark)',
            padding: '10px 18px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '13.5px',
            fontFamily: 'var(--font-mono)',
          }}
        >
          python manage.py train_rf_model --village {villageName} --predict
        </code>
      </div>
    );
  }

  const {
    total_area_hectares,
    valid_pixels,
    bounds,
    breakdown = [],
  } = analytics;

  // Key KPI classes
  const cropland = breakdown.find((c) => c.class_id === 40);
  const treeCover = breakdown.find((c) => c.class_id === 10);
  const builtUp = breakdown.find((c) => c.class_id === 50);
  const water = breakdown.find((c) => c.class_id === 80);

  // Map center from bounds
  const centerLat = bounds ? (bounds[0][0] + bounds[1][0]) / 2 : 25.496;
  const centerLng = bounds ? (bounds[0][1] + bounds[1][1]) / 2 : 83.809;

  return (
    <div className="lulc-analytics-dashboard" style={{ marginTop: '12px' }}>
      {/* Editorial Section 1 Header */}
      <div className="report-section-header">
        <div>
          <h2 className="report-section-title">
            1. AI Land Use &amp; Land Cover Summary — {villageName}
          </h2>
          <p className="report-section-subtitle">
            Multi-modal fusion combining Sentinel-1 SAR, Copernicus DEM topography, and Sentinel-2 optical indices
          </p>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={fetchAnalytics}
          title="Reload LULC statistics"
        >
          <RefreshCw size={14} aria-hidden="true" />
          <span>Refresh Statistics</span>
        </button>
      </div>

      {/* Institutional Model Spec Notice (Solid Earth Surface — No Gradients/Neon) */}
      <div
        className="card"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '14px',
          background: 'var(--color-success-bg)',
          borderColor: 'var(--color-success-border)',
          padding: '16px 20px',
          marginBottom: '22px',
          boxShadow: 'none',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              flexShrink: 0,
            }}
          >
            <Sparkles size={22} aria-hidden="true" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--color-primary-dark)', margin: 0 }}>
                Phase 8 Land Cover Classification Specification
              </h3>
              <span className="badge badge-green">83.02% Model Accuracy</span>
              <span className="badge badge-blue">10m Metric Grid</span>
            </div>
            <p style={{ fontSize: '13.5px', color: 'var(--color-text-primary)', margin: '5px 0 0 0', lineHeight: 1.5 }}>
              <strong>Feature Stack:</strong> Sentinel-1 SAR (VV, VH) + Copernicus DEM (Elevation, Slope) + Sentinel-2 Optical (NDVI, NDWI) with SCL Cloud Masking
            </p>
          </div>
        </div>
      </div>

      {/* Top Stat Cards (KPIs) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
          gap: '16px',
          marginBottom: '26px',
        }}
      >
        {/* Total Area */}
        <div className="card" style={{ padding: '18px 20px', marginBottom: 0 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span className="kpi-label">Total Assessed Area</span>
            <MapPin size={18} style={{ color: 'var(--color-info)' }} aria-hidden="true" />
          </div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
            {total_area_hectares.toLocaleString()}{' '}
            <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>ha</span>
          </div>
          <div className="kpi-subtext" style={{ marginTop: '6px' }}>
            {valid_pixels?.toLocaleString()} aligned 10m grid cells
          </div>
        </div>

        {/* Cropland */}
        <div
          className="card"
          style={{
            padding: '18px 20px',
            marginBottom: 0,
            borderLeft: '4px solid #4A7C59',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span className="kpi-label">Cropland</span>
            <Wheat size={18} style={{ color: '#4A7C59' }} aria-hidden="true" />
          </div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: 'var(--color-primary-dark)', fontFamily: 'var(--font-mono)' }}>
            {cropland ? cropland.hectares : 0}{' '}
            <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>ha</span>
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-success)', fontWeight: 600, marginTop: '6px' }}>
            {cropland ? `${cropland.percentage}% of village area` : '0% of village area'}
          </div>
        </div>

        {/* Tree Cover */}
        <div
          className="card"
          style={{
            padding: '18px 20px',
            marginBottom: 0,
            borderLeft: '4px solid #2D5A3C',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span className="kpi-label">Tree Canopy</span>
            <Trees size={18} style={{ color: '#2D5A3C' }} aria-hidden="true" />
          </div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: '#2D5A3C', fontFamily: 'var(--font-mono)' }}>
            {treeCover ? treeCover.hectares : 0}{' '}
            <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>ha</span>
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-success)', fontWeight: 600, marginTop: '6px' }}>
            {treeCover ? `${treeCover.percentage}% of village area` : '0% of village area'}
          </div>
        </div>

        {/* Built-up */}
        <div
          className="card"
          style={{
            padding: '18px 20px',
            marginBottom: 0,
            borderLeft: '4px solid var(--color-error)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span className="kpi-label">Settlements</span>
            <Home size={18} style={{ color: 'var(--color-error)' }} aria-hidden="true" />
          </div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: 'var(--color-error)', fontFamily: 'var(--font-mono)' }}>
            {builtUp ? builtUp.hectares : 0}{' '}
            <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>ha</span>
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-error)', fontWeight: 600, marginTop: '6px' }}>
            {builtUp ? `${builtUp.percentage}% of village area` : '0% of village area'}
          </div>
        </div>

        {/* Water Bodies */}
        <div
          className="card"
          style={{
            padding: '18px 20px',
            marginBottom: 0,
            borderLeft: '4px solid var(--color-info)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span className="kpi-label">Water Bodies</span>
            <Waves size={18} style={{ color: 'var(--color-info)' }} aria-hidden="true" />
          </div>
          <div style={{ fontSize: '26px', fontWeight: 700, color: 'var(--color-info)', fontFamily: 'var(--font-mono)' }}>
            {water ? water.hectares : 0}{' '}
            <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>ha</span>
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-info)', fontWeight: 600, marginTop: '6px' }}>
            {water ? `${water.percentage}% of village area` : '0% of village area'}
          </div>
        </div>
      </div>

      {/* Editorial Section 2 Header */}
      <div className="report-section-header">
        <div>
          <h2 className="report-section-title">
            2. Hectare Composition &amp; Cartographic Map View
          </h2>
          <p className="report-section-subtitle">
            Detailed class-by-class area ledger alongside spatial verification basemap
          </p>
        </div>
      </div>

      {/* Main Grid: Distribution Breakdown + Spatial Map View */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))',
          gap: '22px',
          marginBottom: '24px',
        }}
      >
        {/* Left Column: Proportional Chart & Class Breakdown List */}
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-header">
            <div className="card-title-group">
              <h3 className="card-title">Land Cover Composition &amp; Area Breakdown</h3>
              <p className="card-subtitle">Hectares computed at 100 m&sup2; per grid cell</p>
            </div>
            <span className="badge badge-gray">10m Resolution</span>
          </div>

          {/* Stacked Proportional Distribution Bar */}
          <div style={{ marginBottom: '20px' }}>
            <div
              style={{
                display: 'flex',
                height: '20px',
                borderRadius: 'var(--radius-sm)',
                overflow: 'hidden',
                border: '1px solid var(--color-border-dark)',
              }}
            >
              {breakdown.map((item) => (
                <div
                  key={`stacked-${item.class_id}`}
                  style={{
                    width: `${item.percentage}%`,
                    backgroundColor: item.color,
                    transition: 'width 0.35s ease',
                  }}
                  title={`${item.name}: ${item.hectares} ha (${item.percentage}%)`}
                />
              ))}
            </div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: '12px',
                fontWeight: 600,
                color: 'var(--color-text-muted)',
                marginTop: '6px',
              }}
            >
              <span>0%</span>
              <span>Village Land Distribution Share</span>
              <span>100%</span>
            </div>
          </div>

          {/* Class Breakdown Rows */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {breakdown.map((item) => {
              const IconComponent = CLASS_ICONS[item.class_id] || Grid;
              return (
                <div
                  key={`row-${item.class_id}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--color-surface-muted)',
                    border: '1px solid var(--color-border-light)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div
                      style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: 'var(--radius-sm)',
                        backgroundColor: item.color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#ffffff',
                        flexShrink: 0,
                      }}
                    >
                      <IconComponent size={16} aria-hidden="true" />
                    </div>
                    <div>
                      <div style={{ fontSize: '14.5px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
                        {item.name}
                      </div>
                      <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                        {item.description}
                      </div>
                    </div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '15.5px', fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
                      {item.hectares.toLocaleString()}{' '}
                      <span style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>ha</span>
                    </div>
                    <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--color-primary-dark)' }}>
                      {item.percentage}% ({item.pixels?.toLocaleString()} px)
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Embedded Leaflet Map Preview */}
        <div
          className="card"
          style={{
            marginBottom: 0,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div className="card-header">
            <div className="card-title-group">
              <h3 className="card-title">
                <Layers size={18} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
                <span>Spatial LULC Map Overlay ({villageName})</span>
              </h3>
              <p className="card-subtitle">Georeferenced raster overlaid on reference imagery</p>
            </div>

            {onNavigateToGis && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={onNavigateToGis}
              >
                <ExternalLink size={14} aria-hidden="true" />
                <span>Open GIS Explorer</span>
              </button>
            )}
          </div>

          {/* Opacity Control Slider */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              background: 'var(--color-surface-muted)',
              border: '1px solid var(--color-border-light)',
              padding: '8px 14px',
              borderRadius: 'var(--radius-sm)',
              marginBottom: '14px',
            }}
          >
            <Sliders size={15} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
            <label
              htmlFor="lulc-opacity-slider"
              style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--color-text-secondary)' }}
            >
              Overlay Opacity:
            </label>
            <input
              id="lulc-opacity-slider"
              type="range"
              min="10"
              max="100"
              value={overlayOpacity}
              onChange={(e) => setOverlayOpacity(Number(e.target.value))}
              style={{ flex: 1, accentColor: 'var(--color-primary)', cursor: 'pointer' }}
            />
            <span
              style={{
                fontSize: '13px',
                fontWeight: 700,
                fontFamily: 'var(--font-mono)',
                color: 'var(--color-text-primary)',
                minWidth: '38px',
                textAlign: 'right',
              }}
            >
              {overlayOpacity}%
            </span>
          </div>

          {/* Leaflet Map Preview Container */}
          <div
            style={{
              flex: 1,
              minHeight: '340px',
              borderRadius: 'var(--radius-md)',
              overflow: 'hidden',
              border: '1px solid var(--color-border-dark)',
              position: 'relative',
            }}
          >
            {bounds && (
              <MapContainer
                center={[centerLat, centerLng]}
                zoom={13}
                maxZoom={22}
                scrollWheelZoom={true}
                style={{ width: '100%', height: '100%', minHeight: '340px' }}
              >
                <LayersControl position="topright">
                  <LayersControl.BaseLayer checked name="Satellite Imagery">
                    <TileLayer
                      attribution="Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS"
                      url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                      maxNativeZoom={18}
                      maxZoom={22}
                    />
                  </LayersControl.BaseLayer>
                  <LayersControl.BaseLayer name="OpenStreetMap">
                    <TileLayer
                      attribution="&copy; OpenStreetMap contributors"
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                      maxNativeZoom={19}
                      maxZoom={22}
                    />
                  </LayersControl.BaseLayer>

                  <LayersControl.Overlay checked name="AI Land Cover Prediction">
                    <ImageOverlay
                      url={getVillagePredictedMapUrl(villageId, overlayOpacity / 100.0)}
                      bounds={bounds}
                      opacity={overlayOpacity / 100.0}
                      zIndex={400}
                    />
                  </LayersControl.Overlay>
                </LayersControl>
              </MapContainer>
            )}

            {/* Embedded Solid Paper Map Legend (No Glassmorphism Blur) */}
            <div
              style={{
                position: 'absolute',
                bottom: '12px',
                left: '12px',
                zIndex: 1000,
                background: '#FFFFFF',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-sm)',
                padding: '10px 12px',
                boxShadow: 'var(--shadow-md)',
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '6px 12px',
                fontSize: '12.5px',
                fontWeight: 600,
                color: 'var(--color-text-primary)',
              }}
            >
              {breakdown.map((item) => (
                <div
                  key={`legend-chip-${item.class_id}`}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <span
                    style={{
                      width: '11px',
                      height: '11px',
                      borderRadius: '2px',
                      backgroundColor: item.color,
                      border: '1px solid rgba(44, 42, 41, 0.2)',
                    }}
                  />
                  <span>{item.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LulcAnalyticsDashboard;
