import React, { useState } from 'react';
import { FileText, Printer, CheckCircle, Database, ShieldCheck, Layers, Clock } from 'lucide-react';

export function Reports({
  villages = [],
  selectedVillage = null,
  onSelectVillage = () => {},
  scenes = [],
}) {
  const targetVillageId = selectedVillage?.id ?? (villages[0]?.id ?? '');
  const activeVillageObj = villages.find((v) => String(v.id) === String(targetVillageId)) || villages[0];
  const villageScenes = scenes.filter((s) => String(s.village) === String(targetVillageId));

  const [activeReportTab, setActiveReportTab] = useState('dossier'); // 'dossier' | 'audit' | 'infra' | 'analytics-export'

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="reports-workspace">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-title-block">
          <h1 className="page-title">Executive Reports & Audits</h1>
          <p className="page-subtitle">
            Village spatial dossiers, satellite acquisition audit logs, and infrastructure compliance records
          </p>
        </div>

        <div className="page-header-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handlePrint}
            title="Print or export PDF report"
          >
            <Printer size={14} />
            Print Dossier / Export PDF
          </button>
        </div>
      </div>

      {/* Report Tabs */}
      <div className="tab-navigation">
        <button
          type="button"
          className={`tab-btn ${activeReportTab === 'dossier' ? 'active' : ''}`}
          onClick={() => setActiveReportTab('dossier')}
        >
          <FileText size={15} />
          Village Spatial Dossier
        </button>
        <button
          type="button"
          className={`tab-btn ${activeReportTab === 'audit' ? 'active' : ''}`}
          onClick={() => setActiveReportTab('audit')}
        >
          <Database size={15} />
          Satellite Acquisition Audit Log
          <span className="badge badge-gray" style={{ marginLeft: 6, fontSize: '10px' }}>
            {scenes.length}
          </span>
        </button>
        <button
          type="button"
          className={`tab-btn ${activeReportTab === 'infra' ? 'active' : ''}`}
          onClick={() => setActiveReportTab('infra')}
        >
          <ShieldCheck size={15} />
          GIS & Database Infrastructure Specs
        </button>
        <button
          type="button"
          className={`tab-btn ${activeReportTab === 'analytics-export' ? 'active' : ''}`}
          onClick={() => setActiveReportTab('analytics-export')}
        >
          <Clock size={15} />
          Bio-Physical Analytics Export
        </button>
      </div>

      {/* Tab 1: Village Spatial Dossier */}
      {activeReportTab === 'dossier' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Village Selector Card */}
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header" style={{ marginBottom: 0, paddingBottom: 0, borderBottom: 'none' }}>
              <div className="card-title-group">
                <h3 className="card-title">Select Village Spatial Dossier</h3>
                <p className="card-subtitle">Generate official spatial coordinates and satellite observation summary</p>
              </div>
              <select
                className="form-select"
                value={targetVillageId}
                onChange={(e) => {
                  const found = villages.find((v) => String(v.id) === String(e.target.value));
                  if (found) onSelectVillage(found);
                }}
                style={{ minWidth: '220px' }}
              >
                {villages.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.district})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Dossier Sheet */}
          {activeVillageObj && (
            <div
              className="card"
              style={{
                border: '2px solid var(--color-border)',
                padding: '28px',
                background: 'var(--color-surface)',
              }}
            >
              {/* Dossier Header */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderBottom: '2px solid var(--color-primary)',
                  paddingBottom: '16px',
                  marginBottom: '20px',
                  flexWrap: 'wrap',
                  gap: '12px',
                }}
              >
                <div>
                  <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--color-primary)' }}>
                    Government of Rajasthan &bull; Smart Village Monitoring System
                  </span>
                  <h2 style={{ margin: '4px 0 0 0', fontSize: '22px', color: 'var(--color-text-primary)' }}>
                    Spatial Dossier: Village {activeVillageObj.name}
                  </h2>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span className="badge badge-green">
                    Active GIS Entity
                  </span>
                  <span style={{ display: 'block', fontSize: '11px', color: 'var(--color-text-muted)', marginTop: 4 }}>
                    Entity ID: #{activeVillageObj.id}
                  </span>
                </div>
              </div>

              {/* Spatial Coordinates & Attributes */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '24px' }}>
                <div style={{ padding: '12px 14px', background: 'var(--color-surface-muted)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-light)' }}>
                  <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'block', textTransform: 'uppercase', fontWeight: 600 }}>Administrative District</span>
                  <strong style={{ fontSize: '14px', color: 'var(--color-text-primary)' }}>{activeVillageObj.district}</strong>
                </div>
                <div style={{ padding: '12px 14px', background: 'var(--color-surface-muted)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-light)' }}>
                  <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'block', textTransform: 'uppercase', fontWeight: 600 }}>State Jurisdiction</span>
                  <strong style={{ fontSize: '14px', color: 'var(--color-text-primary)' }}>{activeVillageObj.state || 'Rajasthan'}</strong>
                </div>
                <div style={{ padding: '12px 14px', background: 'var(--color-surface-muted)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-light)' }}>
                  <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'block', textTransform: 'uppercase', fontWeight: 600 }}>Centroid (EPSG:4326)</span>
                  <strong style={{ fontSize: '13px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)' }}>
                    {activeVillageObj.latitude?.toFixed(6)}°N, {activeVillageObj.longitude?.toFixed(6)}°E
                  </strong>
                </div>
                <div style={{ padding: '12px 14px', background: 'var(--color-surface-muted)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-light)' }}>
                  <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'block', textTransform: 'uppercase', fontWeight: 600 }}>Area (Hectares)</span>
                  <strong style={{ fontSize: '14px', color: 'var(--color-text-primary)' }}>
                    {activeVillageObj.area_hectares != null ? `${activeVillageObj.area_hectares} ha` : 'Survey Pending'}
                  </strong>
                </div>
                <div style={{ padding: '12px 14px', background: 'var(--color-surface-muted)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-light)' }}>
                  <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'block', textTransform: 'uppercase', fontWeight: 600 }}>Census Population</span>
                  <strong style={{ fontSize: '14px', color: 'var(--color-text-primary)' }}>
                    {activeVillageObj.population != null ? activeVillageObj.population.toLocaleString() : 'N/A'}
                  </strong>
                </div>
                <div style={{ padding: '12px 14px', background: 'var(--color-surface-muted)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-light)' }}>
                  <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', display: 'block', textTransform: 'uppercase', fontWeight: 600 }}>PostGIS Boundary Status</span>
                  <strong style={{ fontSize: '13px', color: activeVillageObj.boundary ? 'var(--color-success)' : 'var(--color-text-secondary)' }}>
                    {activeVillageObj.boundary ? 'MultiPolygon Verified' : 'Provisional 2.5km Radial Window'}
                  </strong>
                </div>
              </div>

              {/* Ingested Satellite Scenes for this Village */}
              <div>
                <h4 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: '12px' }}>
                  Associated Satellite Observations ({villageScenes.length})
                </h4>

                {villageScenes.length === 0 ? (
                  <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', fontStyle: 'italic', margin: 0 }}>
                    No satellite observations have been ingested for this village yet.
                  </p>
                ) : (
                  <div className="table-container">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Scene Identifier</th>
                          <th>Acquisition Date</th>
                          <th>Cloud Cover</th>
                          <th>AOI Cloud</th>
                          <th>Bands Ingested</th>
                          <th>Local Storage Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {villageScenes.map((s) => (
                          <tr key={s.id}>
                            <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{s.scene_id}</td>
                            <td>{new Date(s.acquisition_date).toLocaleDateString()}</td>
                            <td>{s.cloud_cover}%</td>
                            <td>{s.aoi_cloud_cover != null ? `${s.aoi_cloud_cover}%` : 'N/A'}</td>
                            <td>{s.bands_count || 7} GeoTIFFs</td>
                            <td>
                              <span className="badge badge-green">
                                <CheckCircle size={11} /> Stored in PostGIS & Media
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Satellite Acquisition Audit Log */}
      {activeReportTab === 'audit' && (
        <div className="card">
          <div className="card-header">
            <div className="card-title-group">
              <h3 className="card-title">
                <Database size={16} style={{ color: 'var(--color-primary)' }} />
                Comprehensive Satellite Data Acquisition Audit Log
              </h3>
              <p className="card-subtitle">
                System-wide register of all ingested Sentinel-2 Level-2A granules, STAC assets, and cloud coverage verifications
              </p>
            </div>
            <span className="badge badge-blue">{scenes.length} Granules Recorded</span>
          </div>

          <div className="card-body">
            {scenes.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--color-text-muted)' }}>
                <p style={{ margin: 0 }}>No satellite records found in PostGIS database.</p>
              </div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Record ID</th>
                      <th>Target Village</th>
                      <th>Sentinel-2 Granule ID</th>
                      <th>Acquisition Time (UTC)</th>
                      <th>Scene Cloud</th>
                      <th>AOI Cloud (SCL)</th>
                      <th>Provider</th>
                      <th>Bands</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scenes.map((s) => {
                      const vObj = villages.find((v) => String(v.id) === String(s.village));
                      return (
                        <tr key={s.id}>
                          <td>#{s.id}</td>
                          <td>
                            <strong>{vObj ? vObj.name : `Village #${s.village}`}</strong>
                            {vObj && <span style={{ display: 'block', fontSize: '11px', color: 'var(--color-text-muted)' }}>{vObj.district}</span>}
                          </td>
                          <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '12px' }}>
                            {s.scene_id}
                          </td>
                          <td>{new Date(s.acquisition_date).toUTCString()}</td>
                          <td>
                            <span className="badge badge-gray">{s.cloud_cover}%</span>
                          </td>
                          <td>
                            {s.aoi_cloud_cover != null ? (
                              <span className="badge badge-green">{s.aoi_cloud_cover}%</span>
                            ) : (
                              <span style={{ color: 'var(--color-text-muted)' }}>N/A</span>
                            )}
                          </td>
                          <td>{s.provider}</td>
                          <td>
                            <span className="badge badge-blue">{s.bands_count || s.bands?.length || 7} Bands</span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Infrastructure Specs */}
      {activeReportTab === 'infra' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header">
              <h3 className="card-title">
                <Database size={16} style={{ color: 'var(--color-primary)' }} />
                Database & Spatial Engines
              </h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--color-border-light)' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>Relational Database:</span>
                <strong style={{ fontSize: '13px' }}>PostgreSQL 18</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--color-border-light)' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>Spatial Extension:</span>
                <strong style={{ fontSize: '13px' }}>PostGIS 3.6.2</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--color-border-light)' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>GIS Geospatial Abstraction:</span>
                <strong style={{ fontSize: '13px' }}>GDAL 3.9.2 & GEOS 3.14.1</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--color-border-light)' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>Spatial Reference System:</span>
                <code style={{ fontSize: '12px' }}>EPSG:4326 (WGS 84)</code>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>Database Name:</span>
                <code style={{ fontSize: '12px' }}>smart_village_db</code>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginBottom: 0 }}>
            <div className="card-header">
              <h3 className="card-title">
                <Layers size={16} style={{ color: 'var(--color-primary)' }} />
                Earth Observation & Remote Sensing
              </h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--color-border-light)' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>Satellite Constellation:</span>
                <strong style={{ fontSize: '13px' }}>Copernicus Sentinel-2A / Sentinel-2B</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--color-border-light)' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>Processing Level:</span>
                <strong style={{ fontSize: '13px' }}>Level-2A (Surface Reflectance BOA)</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--color-border-light)' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>STAC Providers:</span>
                <strong style={{ fontSize: '13px' }}>AWS Earth Search / Microsoft PC</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--color-border-light)' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>Raster Extraction Engine:</span>
                <strong style={{ fontSize: '13px' }}>Rasterio 1.4 & NumPy 2.x</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>Spatial Ground Resolution:</span>
                <strong style={{ fontSize: '13px' }}>10m (VNIR), 20m (SWIR/SCL)</strong>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Bio-Physical Analytics Export (Unimplemented Empty State) */}
      {activeReportTab === 'analytics-export' && (
        <div className="card">
          <div className="card-header">
            <div className="card-title-group">
              <h3 className="card-title">
                <Clock size={16} style={{ color: 'var(--color-primary)' }} />
                Bio-Physical Analytics Export Dossier
              </h3>
              <p className="card-subtitle">Automated monthly vegetation density and water retention report generation</p>
            </div>
            <span className="badge badge-warning">Phase 4 Roadmap</span>
          </div>

          <div
            style={{
              padding: '40px 24px',
              textAlign: 'center',
              background: 'var(--color-surface-muted)',
              borderRadius: 'var(--radius-md)',
              border: '1px dashed var(--color-border-dark)',
            }}
          >
            <Clock size={36} style={{ color: 'var(--color-warning)', marginBottom: 8 }} />
            <h4 style={{ margin: '0 0 6px 0', color: 'var(--color-text-primary)', fontSize: '15px' }}>
              Analytical Report Generation Pending Phase 4
            </h4>
            <p style={{ margin: '0 auto', maxWidth: '480px', fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
              This export module will compile computed NDVI vegetative growth curves, NDWI water body surface area changes, and drought hazard indices once Phase 4 raster analytics are implemented on the Django backend.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default Reports;