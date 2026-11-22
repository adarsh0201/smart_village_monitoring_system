import React, { useMemo } from 'react';
import {
  Building2,
  Satellite,
  Layers,
  Activity,
  ArrowRight,
  Server,
  MapPin,
  ShieldCheck,
} from 'lucide-react';
import StatCard from './StatCard';

function Overview({
  villages = [],
  scenes = [],
  backendStatus = null,
  isConnected = false,
  onNavigate = () => {},
  onSelectVillage = () => {},
}) {
  // Calculate real metrics from backend data
  const totalVillages = villages.length;
  const totalScenes = scenes.length;

  const villagesWithSatellite = useMemo(() => {
    const villageIdsWithScenes = new Set(scenes.map((s) => s.village));
    return villages.filter((v) => villageIdsWithScenes.has(v.id)).length;
  }, [villages, scenes]);

  const totalBandsStored = useMemo(() => {
    return scenes.reduce((acc, s) => acc + (s.bands_count || s.bands?.length || 0), 0);
  }, [scenes]);

  return (
    <div className="overview-page">
      {/* Page Title Header */}
      <div className="page-header">
        <div className="page-header-title-block">
          <h1 className="page-title">Executive Monitoring Overview</h1>
          <p className="page-subtitle">
            Rajasthan rural ground units integrated with Sentinel-2 multi-spectral remote sensing observations
          </p>
        </div>
        <div className="page-header-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onNavigate('gis')}
          >
            Launch GIS Explorer
            <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="kpi-grid">
        <StatCard
          label="Registered Villages"
          value={totalVillages > 0 ? totalVillages : 'Not available'}
          subtext="PostGIS Spatial Units (EPSG:4326)"
          icon={Building2}
          colorClass="green"
        />

        <StatCard
          label="Villages With Satellite Data"
          value={villagesWithSatellite > 0 ? `${villagesWithSatellite} of ${totalVillages}` : '0 Monitored'}
          subtext="Active Sentinel-2 Ingestion Coverage"
          icon={Satellite}
          colorClass="emerald"
        />

        <StatCard
          label="Ingested Satellite Scenes"
          value={totalScenes > 0 ? totalScenes : '0 Acquired'}
          subtext="Sentinel-2 Level-2A BOA Rasters"
          icon={Layers}
          colorClass="blue"
        />

        <StatCard
          label="Spectral Band Products"
          value={totalBandsStored > 0 ? `${totalBandsStored} GeoTIFFs` : '7 Bands Supported'}
          subtext="B02, B03, B04, B08, B11, B12, SCL"
          icon={Activity}
          colorClass="amber"
        />
      </div>

      {/* 2-Column Responsive Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '20px', marginBottom: '24px' }}>
        {/* Left Column: Recent Satellite Acquisitions */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">
                <Satellite size={17} style={{ color: 'var(--color-primary)' }} />
                Recent Satellite Acquisitions
              </h3>
              <p className="card-subtitle">Real Sentinel-2 Level-2A acquisitions clipped to village AOIs</p>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate('satellite')}
            >
              View Ingestion Pipeline
            </button>
          </div>

          {scenes.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
              No satellite scenes ingested yet. Navigate to <strong>Satellite Imagery</strong> to search and clip Sentinel-2 data.
            </div>
          ) : (
            <div className="table-container" style={{ border: 'none' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Scene ID</th>
                    <th>Target Village</th>
                    <th>Acquisition Date</th>
                    <th>AOI Cloud</th>
                    <th>Bands</th>
                  </tr>
                </thead>
                <tbody>
                  {scenes.slice(0, 5).map((scene) => (
                    <tr key={scene.id}>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-primary)', fontWeight: 600 }}>
                        {scene.scene_id}
                      </td>
                      <td>
                        <strong>{scene.village_name || `Village #${scene.village}`}</strong>
                      </td>
                      <td style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                        {new Date(scene.acquisition_date).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </td>
                      <td>
                        <span className="badge badge-green">
                          {scene.aoi_cloud_cover != null ? `${scene.aoi_cloud_cover}%` : `${scene.cloud_cover}%`}
                        </span>
                      </td>
                      <td>
                        <span className="badge badge-gray">{scene.bands_count || scene.bands?.length || 7} Bands</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right Column: Monitored Villages Overview */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">
                <Building2 size={17} style={{ color: 'var(--color-primary)' }} />
                Rajasthan Pilot Villages
              </h3>
              <p className="card-subtitle">Representative agro-climatic zones across Rajasthan</p>
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate('villages')}
            >
              Village Registry
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {villages.map((v) => (
              <div
                key={v.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '10px 14px',
                  background: 'var(--color-surface-muted)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border-light)',
                  transition: 'background var(--transition-fast)',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <strong style={{ fontSize: '13px', color: 'var(--color-primary)' }}>{v.name}</strong>
                    <span className="badge badge-gray">{v.district}</span>
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                    Centroid: {v.latitude?.toFixed(4)}° N, {v.longitude?.toFixed(4)}° E &bull; {v.area_hectares != null ? `${v.area_hectares} ha` : 'Pending Calc'}
                  </span>
                </div>

                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  style={{ padding: '4px 8px', fontSize: '11px' }}
                  onClick={() => {
                    onSelectVillage(v);
                    onNavigate('gis');
                  }}
                >
                  <MapPin size={12} />
                  View in GIS
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* System Infrastructure & Rajasthan Context */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '12px' }}>
            <Server size={17} style={{ color: 'var(--color-primary)' }} />
            System Infrastructure & Pipeline Health
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px dashed var(--color-border-light)' }}>
              <span style={{ color: 'var(--color-text-secondary)' }}>Backend Framework</span>
              <strong>{backendStatus?.backend || 'Django 5.2 REST Framework'}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px dashed var(--color-border-light)' }}>
              <span style={{ color: 'var(--color-text-secondary)' }}>Database & GIS Engine</span>
              <strong>PostgreSQL 18 + PostGIS 3.6</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px dashed var(--color-border-light)' }}>
              <span style={{ color: 'var(--color-text-secondary)' }}>Raster Ingestion Library</span>
              <strong>Rasterio 1.4 + GeoTIFF + GDAL 3.9</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px dashed var(--color-border-light)' }}>
              <span style={{ color: 'var(--color-text-secondary)' }}>STAC Satellite Providers</span>
              <strong>AWS Earth Search / Microsoft Planetary Computer</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
              <span style={{ color: 'var(--color-text-secondary)' }}>Connection Status</span>
              <span className={`badge ${isConnected ? 'badge-green' : 'badge-amber'}`}>
                {isConnected ? 'Active & Ready' : 'Server Offline'}
              </span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="card-title" style={{ marginBottom: '12px' }}>
            <ShieldCheck size={17} style={{ color: 'var(--color-primary)' }} />
            Rajasthan Agro-Climatic Monitoring Protocol
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: 1.6, margin: '0 0 10px' }}>
            The system tracks agricultural stress, watershed changes, and land degradation across Rajasthan&apos;s distinct agro-climatic zones:
          </p>
          <ul style={{ fontSize: '12px', color: 'var(--color-text-secondary)', paddingLeft: '18px', margin: 0, lineHeight: 1.6 }}>
            <li><strong>Southern Aravalli:</strong> Piplantri & Kothariya (Watershed afforestation & soil conservation)</li>
            <li><strong>Shekhawati Semi-Arid:</strong> Mandawa (Groundwater stress & arid crop cycles)</li>
            <li><strong>Western Thar Desert:</strong> Bhadla & Kuldhara (Solar park land change & extreme hyper-arid reference)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default Overview;
