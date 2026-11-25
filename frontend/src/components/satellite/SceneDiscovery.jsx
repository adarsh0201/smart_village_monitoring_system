import React, { useState } from 'react';
import {
  Search,
  Download,
  CheckCircle2,
  AlertCircle,
  Calendar,
  Cloud,
  Layers,
  Sparkles,
  Loader2,
  ArrowRight,
} from 'lucide-react';
import { searchSatelliteScenes, downloadSatelliteScene } from '../../services/api';

export function SceneDiscovery({
  villages = [],
  selectedVillage = null,
  onSelectVillage = () => {},
  onSceneIngested = () => {},
  ingestedSceneIds = new Set(),
  onNavigateToLibrary = () => {},
}) {
  const targetVillageId = selectedVillage?.id ?? (villages[0]?.id ?? '');

  const [startDate, setStartDate] = useState('2024-03-01');
  const [endDate, setEndDate] = useState('2024-03-31');
  const [maxCloudCover, setMaxCloudCover] = useState(20);
  const [bufferKm, setBufferKm] = useState(2.5);

  const [isSearching, setIsSearching] = useState(false);
  const [downloadingSceneId, setDownloadingSceneId] = useState(null);
  const [searchResults, setSearchResults] = useState(null);
  const [searchError, setSearchError] = useState(null);
  const [successBanner, setSuccessBanner] = useState(null);

  const activeVillageObj = villages.find((v) => String(v.id) === String(targetVillageId)) || null;

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!targetVillageId) return;

    setIsSearching(true);
    setSearchError(null);
    setSuccessBanner(null);

    try {
      const data = await searchSatelliteScenes({
        village_id: targetVillageId,
        start_date: startDate,
        end_date: endDate,
        max_cloud_cover: parseFloat(maxCloudCover),
        buffer_km: parseFloat(bufferKm),
      });
      setSearchResults(data);
    } catch (err) {
      console.error('Satellite search error:', err);
      const msg = err.response?.data?.error || err.message || 'Failed to search Sentinel-2 scenes.';
      setSearchError(msg);
    } finally {
      setIsSearching(false);
    }
  };

  const handleDownload = async (sceneId) => {
    setDownloadingSceneId(sceneId);
    setSearchError(null);
    setSuccessBanner(null);

    try {
      const res = await downloadSatelliteScene({
        village_id: targetVillageId,
        scene_id: sceneId,
        buffer_km: parseFloat(bufferKm),
      });

      setSuccessBanner(
        `Scene ${sceneId} successfully ingested! ${res.scene?.bands_count || 7} GeoTIFF spectral bands clipped to village AOI.`
      );

      // Notify parent to refresh library
      onSceneIngested(res.scene);

      // Update local downloaded flag
      if (searchResults?.scenes) {
        setSearchResults({
          ...searchResults,
          scenes: searchResults.scenes.map((s) =>
            s.scene_id === sceneId ? { ...s, is_downloaded: true } : s
          ),
        });
      }
    } catch (err) {
      console.error('Satellite download error:', err);
      const msg = err.response?.data?.error || err.message || 'Failed to download and clip satellite scene.';
      setSearchError(msg);
    } finally {
      setDownloadingSceneId(null);
    }
  };

  const setDatePreset = (preset) => {
    const today = new Date();
    const formatDate = (d) => d.toISOString().split('T')[0];

    if (preset === 'march2024') {
      setStartDate('2024-03-01');
      setEndDate('2024-03-31');
    } else if (preset === 'last30') {
      const past = new Date();
      past.setDate(today.getDate() - 30);
      setStartDate(formatDate(past));
      setEndDate(formatDate(today));
    } else if (preset === 'last90') {
      const past = new Date();
      past.setDate(today.getDate() - 90);
      setStartDate(formatDate(past));
      setEndDate(formatDate(today));
    }
  };

  return (
    <div className="scene-discovery-workspace">
      {/* Alert Banners */}
      {successBanner && (
        <div className="alert-banner alert-success">
          <CheckCircle2 size={18} style={{ flexShrink: 0 }} />
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
            <span>{successBanner}</span>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onNavigateToLibrary}
            >
              Open Ingested Library <ArrowRight size={13} />
            </button>
          </div>
        </div>
      )}

      {searchError && (
        <div className="alert-banner alert-danger">
          <AlertCircle size={18} style={{ flexShrink: 0 }} />
          <span>{searchError}</span>
        </div>
      )}

      {/* Acquisition Configuration Card */}
      <div className="card">
        <div className="card-header">
          <div className="card-title-group">
            <h3 className="card-title">
              <Search size={16} style={{ color: 'var(--color-primary)' }} />
              Sentinel-2 Acquisition & AOI Window Clipping Parameters
            </h3>
            <p className="card-subtitle">
              STAC Provider: AWS Earth Search / Microsoft Planetary Computer &bull; Sentinel-2 Level-2A (Surface Reflectance)
            </p>
          </div>
          <span className="badge badge-green">
            <span style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--color-success)', display: 'inline-block' }}></span>
            STAC v1.0.0 Online
          </span>
        </div>

        <form onSubmit={handleSearch}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '16px' }}>
            {/* Target Village */}
            <div className="form-group">
              <label className="form-label" htmlFor="stac-village-select">Target Village</label>
              <select
                id="stac-village-select"
                className="form-select"
                value={targetVillageId}
                onChange={(e) => {
                  const found = villages.find((v) => String(v.id) === String(e.target.value));
                  if (found) onSelectVillage(found);
                }}
              >
                {villages.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.district})
                  </option>
                ))}
              </select>
              {activeVillageObj && (
                <span className="form-hint">
                  Centroid: {activeVillageObj.latitude?.toFixed(4)}°N, {activeVillageObj.longitude?.toFixed(4)}°E
                </span>
              )}
            </div>

            {/* Date Start */}
            <div className="form-group">
              <label className="form-label" htmlFor="stac-start-date">Start Date (UTC)</label>
              <input
                id="stac-start-date"
                type="date"
                className="form-input"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
              <span className="form-hint">Temporal Window Lower Bound</span>
            </div>

            {/* Date End */}
            <div className="form-group">
              <label className="form-label" htmlFor="stac-end-date">End Date (UTC)</label>
              <input
                id="stac-end-date"
                type="date"
                className="form-input"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
              <span className="form-hint">Temporal Window Upper Bound</span>
            </div>

            {/* Max Cloud Cover */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label className="form-label" htmlFor="stac-cloud">Max Cloud Cover: {maxCloudCover}%</label>
                <span className="badge badge-neutral" style={{ fontSize: '10px' }}>
                  {maxCloudCover <= 10 ? 'Clear' : 'Permissive'}
                </span>
              </div>
              <input
                id="stac-cloud"
                type="range"
                min="0"
                max="50"
                step="5"
                value={maxCloudCover}
                onChange={(e) => setMaxCloudCover(e.target.value)}
                style={{ width: '100%', accentColor: 'var(--color-primary)', marginTop: '4px' }}
              />
              <span className="form-hint">Filters scenes where cloud &le; {maxCloudCover}%</span>
            </div>

            {/* Buffer Distance */}
            <div className="form-group">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label className="form-label" htmlFor="stac-buffer">AOI Buffer: {bufferKm} km</label>
                <span className="badge badge-blue" style={{ fontSize: '10px' }}>
                  Radial Extent
                </span>
              </div>
              <input
                id="stac-buffer"
                type="range"
                min="1.0"
                max="5.0"
                step="0.5"
                value={bufferKm}
                onChange={(e) => setBufferKm(e.target.value)}
                style={{ width: '100%', accentColor: 'var(--color-primary)', marginTop: '4px' }}
              />
              <span className="form-hint">Provisional bounding box around centroid</span>
            </div>
          </div>

          {/* Presets and Search Button Bar */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
            paddingTop: '14px',
            borderTop: '1px solid var(--color-border-light)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', marginRight: '4px' }}>
                Quick Presets:
              </span>
              <button
                type="button"
                className="btn-preset"
                onClick={() => setDatePreset('march2024')}
                title="Spring 2024 benchmark imagery"
              >
                <Sparkles size={12} style={{ display: 'inline', marginRight: 4, verticalAlign: 'middle', color: 'var(--color-primary)' }} />
                March 2024 (Baseline)
              </button>
              <button
                type="button"
                className="btn-preset"
                onClick={() => setDatePreset('last30')}
              >
                Last 30 Days
              </button>
              <button
                type="button"
                className="btn-preset"
                onClick={() => setDatePreset('last90')}
              >
                Last 90 Days
              </button>
            </div>

            <button
              type="submit"
              disabled={isSearching}
              className="btn btn-primary"
              style={{ minWidth: '220px' }}
            >
              {isSearching ? (
                <>
                  <Loader2 size={15} className="spinning" />
                  Querying STAC Provider...
                </>
              ) : (
                <>
                  <Search size={15} />
                  Search Sentinel-2 Scenes
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Available Scenes Table */}
      {searchResults && (
        <div className="card">
          <div className="card-header">
            <div className="card-title-group">
              <h3 className="card-title">
                Available Sentinel-2 Level-2A Granules ({searchResults.total_scenes_found})
              </h3>
              <p className="card-subtitle">
                Target: <strong>{searchResults.village.name}</strong> ({searchResults.village.district}) &bull;{' '}
                {searchResults.aoi.description}
              </p>
            </div>
            <span className="badge badge-blue">
              {searchResults.scenes.length} Granules Matched
            </span>
          </div>

          {searchResults.scenes.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--color-text-secondary)' }}>
              <Cloud size={36} style={{ color: 'var(--color-text-muted)', marginBottom: '8px' }} />
              <h4 style={{ margin: '0 0 4px 0', color: 'var(--color-text-primary)' }}>No Matching Sentinel-2 Granules Found</h4>
              <p style={{ margin: 0, fontSize: '13px' }}>
                No scenes satisfied the cloud cover threshold (&le; {maxCloudCover}%) in this temporal window.
              </p>
              <span style={{ fontSize: '12px', color: 'var(--color-primary)', marginTop: 8, display: 'inline-block' }}>
                Tip: Try selecting the "March 2024 (Baseline)" preset or increasing max cloud cover.
              </span>
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Scene ID & Granule</th>
                    <th>Acquisition Date (UTC)</th>
                    <th>Cloud Cover</th>
                    <th>Available Spectral Assets</th>
                    <th>Ingestion Status</th>
                    <th style={{ textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {searchResults.scenes.map((scene) => {
                    const isDownloading = downloadingSceneId === scene.scene_id;
                    const isDownloaded = scene.is_downloaded || ingestedSceneIds.has(scene.scene_id);

                    return (
                      <tr key={scene.scene_id} style={{ background: isDownloaded ? 'var(--color-success-bg)' : undefined }}>
                        <td>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '12px', color: 'var(--color-text-primary)' }}>
                              {scene.scene_id}
                            </span>
                            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                              <span className="badge badge-gray" style={{ fontSize: '10px', padding: '1px 5px' }}>
                                Tile {scene.tile_id}
                              </span>
                              <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                                L2A BOA Reflectance
                              </span>
                            </div>
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '12px' }}>
                            <Calendar size={13} style={{ color: 'var(--color-text-muted)' }} />
                            {scene.acquisition_date ? new Date(scene.acquisition_date).toLocaleString() : 'N/A'}
                          </div>
                        </td>
                        <td>
                          <span
                            className={`badge ${
                              scene.cloud_cover < 5 ? 'badge-green' : scene.cloud_cover < 20 ? 'badge-blue' : 'badge-amber'
                            }`}
                          >
                            {scene.cloud_cover}%
                          </span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                            {['B02', 'B03', 'B04', 'B08', 'B11', 'B12', 'SCL'].map((b) => {
                              const isPresent = !!scene.band_assets?.[b];
                              return (
                                <span
                                  key={b}
                                  style={{
                                    fontSize: '10px',
                                    fontWeight: 600,
                                    padding: '1px 5px',
                                    borderRadius: '3px',
                                    background: isPresent ? 'var(--color-success-bg)' : 'var(--color-surface-hover)',
                                    color: isPresent ? 'var(--color-primary-dark)' : 'var(--color-text-muted)',
                                    border: isPresent ? '1px solid var(--color-success-border)' : '1px dashed var(--color-border)',
                                  }}
                                  title={isPresent ? `Band ${b} available on STAC` : `Band ${b} unavailable`}
                                >
                                  {b}
                                </span>
                              );
                            })}
                          </div>
                        </td>
                        <td>
                          {isDownloaded ? (
                            <span className="badge badge-green">
                              <CheckCircle2 size={12} />
                              Ingested (PostGIS)
                            </span>
                          ) : (
                            <span className="badge badge-gray">STAC Catalog Ready</span>
                          )}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          {isDownloaded ? (
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={onNavigateToLibrary}
                            >
                              <Layers size={13} />
                              View Ingested Bands
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="btn btn-primary btn-sm"
                              disabled={isDownloading}
                              onClick={() => handleDownload(scene.scene_id)}
                            >
                              {isDownloading ? (
                                <>
                                  <Loader2 size={13} className="spinning" />
                                  Clipping AOI...
                                </>
                              ) : (
                                <>
                                  <Download size={13} />
                                  Download & Clip AOI
                                </>
                              )}
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default SceneDiscovery;