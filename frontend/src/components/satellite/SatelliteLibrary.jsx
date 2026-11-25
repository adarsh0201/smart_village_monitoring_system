import React, { useState } from 'react';
import { Database, Calendar, Cloud, HardDrive, Layers, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';
import SpectralBandPanel from './SpectralBandPanel';
import EmptyState from '../common/EmptyState';

export function SatelliteLibrary({
  villages = [],
  selectedVillage = null,
  onSelectVillage = () => {},
  scenes = [],
  onNavigateToDiscovery = () => {},
}) {
  const [selectedVillageFilter, setSelectedVillageFilter] = useState(selectedVillage?.id || 'all');
  const [expandedSceneId, setExpandedSceneId] = useState(scenes[0]?.id || null);

  const filteredScenes = scenes.filter((s) => {
    if (selectedVillageFilter === 'all') return true;
    return String(s.village) === String(selectedVillageFilter);
  });

  const toggleExpand = (sceneId) => {
    setExpandedSceneId((prev) => (prev === sceneId ? null : sceneId));
  };

  return (
    <div className="satellite-library-workspace">
      {/* Header filter card */}
      <div className="card">
        <div className="card-header" style={{ marginBottom: 0, paddingBottom: 0, borderBottom: 'none' }}>
          <div className="card-title-group">
            <h3 className="card-title">
              <HardDrive size={16} style={{ color: 'var(--color-primary)' }} />
              Ingested Satellite Rasters & Spectral Band Repository
            </h3>
            <p className="card-subtitle">
              Surface Reflectance GeoTIFF assets stored in local filesystem (<code>backend/media/satellite/</code>) and indexed in PostGIS
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <label htmlFor="library-village-filter" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
              Filter Village:
            </label>
            <select
              id="library-village-filter"
              className="form-select"
              value={selectedVillageFilter}
              onChange={(e) => {
                const val = e.target.value;
                setSelectedVillageFilter(val);
                if (val !== 'all') {
                  const found = villages.find((v) => String(v.id) === String(val));
                  if (found) onSelectVillage(found);
                }
              }}
              style={{ minWidth: '200px' }}
            >
              <option value="all">All Villages ({scenes.length} Scenes)</option>
              {villages.map((v) => {
                const count = scenes.filter((s) => String(s.village) === String(v.id)).length;
                return (
                  <option key={v.id} value={v.id}>
                    {v.name} ({count} scenes)
                  </option>
                );
              })}
            </select>
          </div>
        </div>
      </div>

      {/* Scenes List or Empty State */}
      {filteredScenes.length === 0 ? (
        <EmptyState
          icon={HardDrive}
          title="No Ingested Scenes Found"
          description={
            selectedVillageFilter === 'all'
              ? 'No Sentinel-2 scenes have been ingested into the system yet.'
              : 'No Sentinel-2 scenes have been ingested yet for this specific village.'
          }
          actionLabel="Query STAC & Ingest Satellite Data"
          onAction={onNavigateToDiscovery}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {filteredScenes.map((scene) => {
            const isExpanded = expandedSceneId === scene.id;
            const villageObj = villages.find((v) => String(v.id) === String(scene.village));

            return (
              <div
                key={scene.id}
                className="card"
                style={{
                  border: isExpanded ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                  boxShadow: isExpanded ? 'var(--shadow-md)' : 'var(--shadow-sm)',
                  marginBottom: 0,
                  padding: 0,
                  overflow: 'hidden',
                }}
              >
                {/* Scene summary banner (clickable) */}
                <div
                  onClick={() => toggleExpand(scene.id)}
                  style={{
                    padding: '16px 20px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    background: isExpanded ? 'var(--color-success-bg)' : 'var(--color-surface)',
                    userSelect: 'none',
                    borderBottom: isExpanded ? '1px solid var(--color-border-light)' : 'none',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: 1, flexWrap: 'wrap' }}>
                    <div
                      style={{
                        width: 40,
                        height: 40,
                        borderRadius: 'var(--radius-md)',
                        background: isExpanded ? 'var(--color-surface)' : 'var(--color-surface-muted)',
                        border: '1px solid var(--color-border)',
                        color: isExpanded ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <Layers size={20} />
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 700, fontSize: '14px', color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
                          {scene.scene_id}
                        </span>
                        <span className="badge badge-green">
                          <CheckCircle size={11} /> {scene.processing_level || 'Level-2A'}
                        </span>
                        <span className="badge badge-blue">
                          {scene.provider || 'AWS Earth Search'}
                        </span>
                        {villageObj && (
                          <span className="badge badge-gray">
                            AOI: {villageObj.name} ({villageObj.district})
                          </span>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '12px', color: 'var(--color-text-secondary)', flexWrap: 'wrap' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Calendar size={13} style={{ color: 'var(--color-text-muted)' }} />
                          Acquisition: <strong>{new Date(scene.acquisition_date).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })} UTC</strong>
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Cloud size={13} style={{ color: 'var(--color-text-muted)' }} />
                          Scene Cloud: <strong>{scene.cloud_cover}%</strong>
                        </span>
                        {scene.aoi_cloud_cover != null && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--color-success)' }}>
                            <CheckCircle size={13} />
                            AOI Cloud: <strong>{scene.aoi_cloud_cover}%</strong> (SCL validated)
                          </span>
                        )}
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Database size={13} style={{ color: 'var(--color-text-muted)' }} />
                          Bands: <strong>{scene.bands_count || scene.bands?.length || 0} GeoTIFFs</strong>
                        </span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      aria-label="Toggle band view"
                    >
                      {isExpanded ? <ChevronUp size={15} aria-hidden="true" /> : <ChevronDown size={15} aria-hidden="true" />}
                      <span>{isExpanded ? 'Hide Bands' : 'Inspect Bands'}</span>
                    </button>
                  </div>
                </div>

                {/* Expanded Spectral Band Details */}
                {isExpanded && (
                  <div style={{ padding: '16px 20px', background: 'var(--color-surface)' }}>
                    <SpectralBandPanel scene={scene} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default SatelliteLibrary;