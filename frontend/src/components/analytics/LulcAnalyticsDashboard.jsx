import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Layers,
  MapPin,
  TrendingUp,
  RefreshCw,
  ExternalLink,
  Sliders,
  CheckCircle2,
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
import L from 'leaflet';
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
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [overlayOpacity, setOverlayOpacity] = useState(85);

  const fetchAnalytics = async () => {
    if (!villageId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getVillageLulcAnalytics(villageId);
      setAnalytics(data);
    } catch (err) {
      console.error('Failed to load LULC analytics:', err);
      setError(err?.response?.data?.error || err.message || 'Failed to fetch analytics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [villageId]);

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 20px', minHeight: '380px' }}>
        <div className="spinner" style={{ width: '36px', height: '36px', marginBottom: '16px' }}></div>
        <span style={{ fontSize: '14px', color: 'var(--color-text-secondary)' }}>
          Extracting AI LULC pixel statistics & raster boundaries for {villageName}...
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="alert-banner alert-danger" style={{ margin: '20px 0' }}>
        <AlertCircle size={20} />
        <div style={{ flex: 1 }}>
          <strong>Error loading LULC analytics:</strong> {error}
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={fetchAnalytics}>
          <RefreshCw size={13} /> Retry
        </button>
      </div>
    );
  }

  if (!analytics || !analytics.available) {
    return (
      <div style={{ background: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: '12px', padding: '40px 24px', textAlign: 'center', margin: '20px 0' }}>
        <Sparkles size={36} color="#94a3b8" style={{ marginBottom: '12px' }} />
        <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#334155', marginBottom: '6px' }}>
          AI Classification Pending for {villageName}
        </h3>
        <p style={{ fontSize: '13px', color: '#64748b', maxWidth: '480px', margin: '0 auto 16px auto', lineHeight: 1.5 }}>
          The multi-modal Random Forest model has not yet been executed for this village. You can generate it by running the Django command:
        </p>
        <code style={{ display: 'inline-block', background: '#0f172a', color: '#38bdf8', padding: '8px 16px', borderRadius: '6px', fontSize: '12px', fontFamily: 'monospace' }}>
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
    model_type,
    features,
  } = analytics;

  // Key KPI classes
  const cropland = breakdown.find((c) => c.class_id === 40);
  const treeCover = breakdown.find((c) => c.class_id === 10);
  const builtUp = breakdown.find((c) => c.class_id === 50);
  const water = breakdown.find((c) => c.class_id === 80);
  const grassland = breakdown.find((c) => c.class_id === 30);

  // Map center from bounds
  const centerLat = bounds ? (bounds[0][0] + bounds[1][0]) / 2 : 25.496;
  const centerLng = bounds ? (bounds[0][1] + bounds[1][1]) / 2 : 83.809;

  return (
    <div className="lulc-analytics-dashboard" style={{ marginTop: '16px' }}>
      {/* Model Spec Banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          background: 'linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%)',
          border: '1px solid #bbf7d0',
          borderRadius: '10px',
          padding: '14px 18px',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: '#22c55e', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ffffff' }}>
            <Sparkles size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#14532d', margin: 0 }}>
                Phase 8 AI Land Use & Land Cover Classification
              </h3>
              <span className="badge badge-green" style={{ fontSize: '11px', padding: '3px 8px' }}>
                83.02% Accuracy
              </span>
              <span className="badge badge-blue" style={{ fontSize: '11px', padding: '3px 8px' }}>
                10m Metric Grid
              </span>
            </div>
            <p style={{ fontSize: '12px', color: '#166534', margin: '4px 0 0 0' }}>
              <strong>Multi-Modal Feature Stack:</strong> Sentinel-1 SAR (VV, VH) + Copernicus DEM (Elevation, Slope) + Sentinel-2 Optical (NDVI, NDWI) with SCL Cloud Masking
            </p>
          </div>
        </div>

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={fetchAnalytics}
          title="Reload LULC statistics"
        >
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {/* Top Stat Cards (KPIs) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '14px',
          marginBottom: '24px',
        }}
      >
        {/* Total Area */}
        <div className="card" style={{ padding: '16px', background: '#ffffff', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>Total Village Area</span>
            <MapPin size={18} color="#0284c7" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#0f172a' }}>
            {total_area_hectares.toLocaleString()} <span style={{ fontSize: '14px', fontWeight: 500, color: '#64748b' }}>ha</span>
          </div>
          <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
            {valid_pixels?.toLocaleString()} aligned 10m grid cells
          </div>
        </div>

        {/* Cropland */}
        <div className="card" style={{ padding: '16px', background: '#ffffff', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)', borderLeft: '4px solid #4caf50' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>Cropland</span>
            <Wheat size={18} color="#4caf50" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#1b5e20' }}>
            {cropland ? cropland.hectares : 0} <span style={{ fontSize: '14px', fontWeight: 500, color: '#64748b' }}>ha</span>
          </div>
          <div style={{ fontSize: '11px', color: '#4caf50', fontWeight: 600, marginTop: '4px' }}>
            {cropland ? `${cropland.percentage}% of village area` : '0%'}
          </div>
        </div>

        {/* Tree Cover */}
        <div className="card" style={{ padding: '16px', background: '#ffffff', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)', borderLeft: '4px solid #1b5e20' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>Tree Canopy</span>
            <Trees size={18} color="#1b5e20" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#1b5e20' }}>
            {treeCover ? treeCover.hectares : 0} <span style={{ fontSize: '14px', fontWeight: 500, color: '#64748b' }}>ha</span>
          </div>
          <div style={{ fontSize: '11px', color: '#16a34a', fontWeight: 600, marginTop: '4px' }}>
            {treeCover ? `${treeCover.percentage}% of village area` : '0%'}
          </div>
        </div>

        {/* Built-up */}
        <div className="card" style={{ padding: '16px', background: '#ffffff', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)', borderLeft: '4px solid #f44336' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>Settlements</span>
            <Home size={18} color="#f44336" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#b91c1c' }}>
            {builtUp ? builtUp.hectares : 0} <span style={{ fontSize: '14px', fontWeight: 500, color: '#64748b' }}>ha</span>
          </div>
          <div style={{ fontSize: '11px', color: '#ef4444', fontWeight: 600, marginTop: '4px' }}>
            {builtUp ? `${builtUp.percentage}% of village area` : '0%'}
          </div>
        </div>

        {/* Water Bodies */}
        <div className="card" style={{ padding: '16px', background: '#ffffff', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)', borderLeft: '4px solid #2196f3' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>Water Bodies</span>
            <Waves size={18} color="#2196f3" />
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#0369a1' }}>
            {water ? water.hectares : 0} <span style={{ fontSize: '14px', fontWeight: 500, color: '#64748b' }}>ha</span>
          </div>
          <div style={{ fontSize: '11px', color: '#0284c7', fontWeight: 600, marginTop: '4px' }}>
            {water ? `${water.percentage}% of village area` : '0%'}
          </div>
        </div>
      </div>

      {/* Main Grid: Distribution Chart + Spatial Map View */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(440px, 1fr))', gap: '20px', marginBottom: '24px' }}>
        {/* Left Column: Proportional Chart & Class Breakdown Table */}
        <div className="card" style={{ padding: '20px', background: '#ffffff', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
              Land Cover Composition & Area Breakdown
            </h4>
            <span style={{ fontSize: '12px', color: '#64748b' }}>10m Resolution</span>
          </div>

          {/* Stacked Proportional Distribution Bar */}
          <div style={{ marginBottom: '18px' }}>
            <div style={{ display: 'flex', height: '18px', borderRadius: '6px', overflow: 'hidden', boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.1)' }}>
              {breakdown.map((item) => (
                <div
                  key={`stacked-${item.class_id}`}
                  style={{
                    width: `${item.percentage}%`,
                    backgroundColor: item.color,
                    transition: 'width 0.4s ease',
                  }}
                  title={`${item.name}: ${item.hectares} ha (${item.percentage}%)`}
                />
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
              <span>0%</span>
              <span>Village Land Distribution</span>
              <span>100%</span>
            </div>
          </div>

          {/* Class Breakdown List / Table */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {breakdown.map((item) => {
              const IconComponent = CLASS_ICONS[item.class_id] || Grid;
              return (
                <div
                  key={`row-${item.class_id}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    background: '#f8fafc',
                    border: '1px solid #f1f5f9',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div
                      style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '6px',
                        backgroundColor: item.color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#ffffff',
                        flexShrink: 0,
                      }}
                    >
                      <IconComponent size={15} />
                    </div>
                    <div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: '#1e293b' }}>
                        {item.name}
                      </div>
                      <div style={{ fontSize: '11px', color: '#64748b' }}>
                        {item.description}
                      </div>
                    </div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#0f172a' }}>
                      {item.hectares.toLocaleString()} <span style={{ fontSize: '11px', fontWeight: 500, color: '#64748b' }}>ha</span>
                    </div>
                    <div style={{ fontSize: '11px', fontWeight: 600, color: '#16a34a' }}>
                      {item.percentage}% ({item.pixels?.toLocaleString()} px)
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Embedded Leaflet Map Preview */}
        <div className="card" style={{ padding: '20px', background: '#ffffff', borderRadius: '10px', border: '1px solid #e2e8f0', boxShadow: 'var(--shadow-sm)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={17} color="#2e7d32" />
              <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                Spatial LULC Map Overlay (Gahmar)
              </h4>
            </div>

            {onNavigateToGis && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={onNavigateToGis}
                style={{ fontSize: '11px', padding: '4px 8px' }}
              >
                <ExternalLink size={12} /> GIS Explorer
              </button>
            )}
          </div>

          {/* Opacity Control Slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: '#f8fafc', padding: '6px 12px', borderRadius: '6px', marginBottom: '12px' }}>
            <Sliders size={14} color="#64748b" />
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#475569' }}>Overlay Opacity:</span>
            <input
              type="range"
              min="10"
              max="100"
              value={overlayOpacity}
              onChange={(e) => setOverlayOpacity(Number(e.target.value))}
              style={{ flex: 1, accentColor: '#16a34a' }}
            />
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#1e293b', minWidth: '32px' }}>
              {overlayOpacity}%
            </span>
          </div>

          {/* Leaflet Map Preview Container */}
          <div style={{ flex: 1, minHeight: '320px', borderRadius: '8px', overflow: 'hidden', border: '1px solid #cbd5e1', position: 'relative' }}>
            {bounds && (
              <MapContainer
                center={[centerLat, centerLng]}
                zoom={13}
                maxZoom={22}
                scrollWheelZoom={true}
                style={{ width: '100%', height: '100%', minHeight: '320px' }}
              >
                <LayersControl position="topright">
                  <LayersControl.BaseLayer checked name="Satellite Imagery">
                    <TileLayer
                      attribution='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS'
                      url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                      maxNativeZoom={18}
                      maxZoom={22}
                    />
                  </LayersControl.BaseLayer>
                  <LayersControl.BaseLayer name="OpenStreetMap">
                    <TileLayer
                      attribution='&copy; OpenStreetMap contributors'
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

            {/* Embedded Floating Map Legend */}
            <div
              style={{
                position: 'absolute',
                bottom: '12px',
                left: '12px',
                zIndex: 1000,
                background: 'rgba(255, 255, 255, 0.94)',
                backdropFilter: 'blur(4px)',
                borderRadius: '6px',
                padding: '8px 10px',
                boxShadow: '0 2px 6px rgba(0,0,0,0.15)',
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '4px 10px',
                fontSize: '11px',
              }}
            >
              {breakdown.map((item) => (
                <div key={`legend-chip-${item.class_id}`} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <span style={{ width: '10px', height: '10px', borderRadius: '2px', backgroundColor: item.color }} />
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
