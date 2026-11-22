import React, { useState, useEffect, useMemo } from 'react';
import { searchSatelliteScenes, downloadSatelliteScene, getSatelliteScenes } from '../services/api';

function SatelliteAcquisition({ villages = [], selectedVillage = null, onSelectVillage = () => {} }) {
  // Selection state
  const [userSelectedVillageId, setUserSelectedVillageId] = useState(null);
  const targetVillageId = userSelectedVillageId ?? selectedVillage?.id ?? (villages[0]?.id ?? '');

  const [startDate, setStartDate] = useState('2024-03-01');
  const [endDate, setEndDate] = useState('2024-03-31');
  const [maxCloudCover, setMaxCloudCover] = useState(20);
  const [bufferKm, setBufferKm] = useState(2.5);

  // Search & Download states
  const [isSearching, setIsSearching] = useState(false);
  const [downloadingSceneId, setDownloadingSceneId] = useState(null);
  const [searchResults, setSearchResults] = useState(null);
  const [searchError, setSearchError] = useState(null);
  const [ingestedScenes, setIngestedScenes] = useState([]);
  const [selectedSceneForInspection, setSelectedSceneForInspection] = useState(null);
  const [successBanner, setSuccessBanner] = useState(null);

  // Load existing ingested scenes for target village
  useEffect(() => {
    let isMounted = true;
    if (!targetVillageId) return;

    async function fetchIngested() {
      try {
        const data = await getSatelliteScenes(targetVillageId);
        if (isMounted) {
          const scenesList = Array.isArray(data) ? data : [];
          setIngestedScenes(scenesList);
          if (scenesList.length > 0) {
            setSelectedSceneForInspection((prev) => {
              if (prev && scenesList.some((s) => s.id === prev.id)) return prev;
              return scenesList[0];
            });
          }
        }
      } catch (err) {
        console.warn('Could not load ingested scenes:', err);
      }
    }

    fetchIngested();
    return () => {
      isMounted = false;
    };
  }, [targetVillageId]);

  const activeVillageObj = useMemo(() => {
    return villages.find((v) => String(v.id) === String(targetVillageId)) || null;
  }, [villages, targetVillageId]);

  // Handle STAC search
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

  // Handle Scene Download and Windowed Clipping
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
        `Scene ${sceneId} successfully ingested! ${res.scene.bands_count || 7} GeoTIFF spectral bands clipped to village AOI.`
      );

      // Refresh ingested scenes
      const refreshedScenes = await getSatelliteScenes(targetVillageId);
      setIngestedScenes(Array.isArray(refreshedScenes) ? refreshedScenes : []);
      setSelectedSceneForInspection(res.scene);

      // Mark scene as downloaded in local search results
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

  // Quick preset dates
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
    <section className="satellite-acquisition-section">
      <div className="section-header">
        <div>
          <h2 className="section-title">Satellite Data Acquisition Pipeline</h2>
          <p className="section-subtitle">
            Sentinel-2 Level-2A Surface Reflectance (Multi-Spectral Bands) &bull; Cloud-Optimized GeoTIFF AOI Ingestion
          </p>
        </div>
        <div className="provider-pill">
          <span className="dot-live"></span>
          <span>STAC Provider: AWS Earth Search / Microsoft Planetary Computer</span>
        </div>
      </div>

      {successBanner && (
        <div className="satellite-alert-banner success">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          <span>{successBanner}</span>
        </div>
      )}

      {searchError && (
        <div className="satellite-alert-banner error">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <span>{searchError}</span>
        </div>
      )}

      {/* Control Query Panel */}
      <div className="satellite-query-panel">
        <form onSubmit={handleSearch} className="query-grid">
          {/* Target Village */}
          <div className="query-field">
            <label htmlFor="village-select">Target Village</label>
            <select
              id="village-select"
              value={targetVillageId}
              onChange={(e) => {
                const newId = e.target.value;
                setUserSelectedVillageId(newId);
                const found = villages.find((v) => String(v.id) === String(newId));
                if (found) onSelectVillage(found);
              }}
              className="query-input select"
            >
              {villages.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name} ({v.district}, {v.state})
                </option>
              ))}
            </select>
            {activeVillageObj && (
              <span className="field-hint">
                Centroid: {activeVillageObj.latitude?.toFixed(4)}° N, {activeVillageObj.longitude?.toFixed(4)}° E
              </span>
            )}
          </div>

          {/* Date Range Start */}
          <div className="query-field">
            <label htmlFor="start-date">Acquisition Start Date</label>
            <input
              id="start-date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="query-input"
              required
            />
          </div>

          {/* Date Range End */}
          <div className="query-field">
            <label htmlFor="end-date">Acquisition End Date</label>
            <input
              id="end-date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="query-input"
              required
            />
          </div>

          {/* Max Cloud Cover */}
          <div className="query-field">
            <label htmlFor="cloud-cover">Max Cloud Cover: {maxCloudCover}%</label>
            <input
              id="cloud-cover"
              type="range"
              min="0"
              max="50"
              step="5"
              value={maxCloudCover}
              onChange={(e) => setMaxCloudCover(e.target.value)}
              className="query-range"
            />
            <span className="field-hint">Filters scenes with clouds &le; {maxCloudCover}%</span>
          </div>

          {/* AOI Buffer */}
          <div className="query-field">
            <label htmlFor="buffer-distance">Provisional AOI Buffer: {bufferKm} km</label>
            <input
              id="buffer-distance"
              type="range"
              min="1.0"
              max="5.0"
              step="0.5"
              value={bufferKm}
              onChange={(e) => setBufferKm(e.target.value)}
              className="query-range"
            />
            <span className="field-hint">
              Circular centroid buffer &bull; Provisional AOI
            </span>
          </div>

          {/* Actions & Presets */}
          <div className="query-actions-wrapper">
            <label className="label-presets">Quick Date Presets</label>
            <div className="preset-buttons-row">
              <button
                type="button"
                className="btn-preset"
                onClick={() => setDatePreset('march2024')}
                title="Spring 2024 benchmark imagery"
              >
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
              className="btn-search-stac"
            >
              {isSearching ? (
                <>
                  <span className="btn-spinner"></span>
                  Searching STAC Catalog...
                </>
              ) : (
                <>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  </svg>
                  Search Available Sentinel-2 Scenes
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Search Results Display */}
      {searchResults && (
        <div className="satellite-results-card">
          <div className="results-header">
            <div>
              <h3 className="results-title">
                Available Sentinel-2 L2A Scenes ({searchResults.total_scenes_found})
              </h3>
              <p className="results-sub">
                Target: <strong>{searchResults.village.name}</strong> &bull; {searchResults.aoi.description}
              </p>
            </div>
          </div>

          {searchResults.scenes.length === 0 ? (
            <div className="empty-results-box">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
              <p>No Sentinel-2 scenes found matching cloud filter &le; {maxCloudCover}% in this date window.</p>
              <span className="hint-text">Try expanding the date range or increasing the max cloud percentage.</span>
            </div>
          ) : (
            <div className="table-responsive">
              <table className="scenes-table">
                <thead>
                  <tr>
                    <th>Scene ID & Granule</th>
                    <th>Acquisition Date (UTC)</th>
                    <th>Scene Cloud Cover</th>
                    <th>Available Spectral Bands</th>
                    <th>Ingestion Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {searchResults.scenes.map((scene) => {
                    const isDownloading = downloadingSceneId === scene.scene_id;
                    const isDownloaded = scene.is_downloaded || ingestedScenes.some((s) => s.scene_id === scene.scene_id);

                    return (
                      <tr key={scene.scene_id} className={isDownloaded ? 'row-downloaded' : ''}>
                        <td className="cell-scene-id">
                          <div className="scene-id-block">
                            <span className="scene-name">{scene.scene_id}</span>
                            <span className="badge-tile">Tile {scene.tile_id}</span>
                          </div>
                        </td>
                        <td className="cell-date">
                          {scene.acquisition_date ? new Date(scene.acquisition_date).toLocaleString() : 'N/A'}
                        </td>
                        <td>
                          <span className={`badge-cloud ${scene.cloud_cover < 5 ? 'clear' : scene.cloud_cover < 20 ? 'moderate' : 'cloudy'}`}>
                            {scene.cloud_cover}%
                          </span>
                        </td>
                        <td>
                          <div className="band-pills-row">
                            {['B02', 'B03', 'B04', 'B08', 'B11', 'B12', 'SCL'].map((b) => (
                              <span
                                key={b}
                                className={`pill-band ${scene.band_assets[b] ? 'present' : 'missing'}`}
                                title={scene.band_assets[b] ? `Band ${b} available` : `Band ${b} unavailable`}
                              >
                                {b}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td>
                          {isDownloaded ? (
                            <span className="badge-status-completed">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                                <polyline points="20 6 9 17 4 12"></polyline>
                              </svg>
                              Ingested (PostGIS)
                            </span>
                          ) : (
                            <span className="badge-status-ready">STAC Catalog Ready</span>
                          )}
                        </td>
                        <td>
                          {isDownloaded ? (
                            <button
                              type="button"
                              className="btn-inspect-bands"
                              onClick={() => {
                                const found = ingestedScenes.find((s) => s.scene_id === scene.scene_id);
                                if (found) setSelectedSceneForInspection(found);
                              }}
                            >
                              View Band GeoTIFFs
                            </button>
                          ) : (
                            <button
                              type="button"
                              className="btn-download-clip"
                              disabled={isDownloading}
                              onClick={() => handleDownload(scene.scene_id)}
                            >
                              {isDownloading ? (
                                <>
                                  <span className="btn-spinner"></span>
                                  Clipping AOI...
                                </>
                              ) : (
                                <>
                                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                    <polyline points="7 10 12 15 17 10"></polyline>
                                    <line x1="12" y1="15" x2="12" y2="3"></line>
                                  </svg>
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

      {/* Ingested Scenes Library & Band Explorer */}
      <div className="ingested-library-section">
        <div className="library-header">
          <div>
            <h3 className="results-title">
              Locally Stored Satellite GeoTIFF Products ({ingestedScenes.length} Ingested Scenes)
            </h3>
            <p className="results-sub">
              Atmospherically corrected Surface Reflectance rasters clipped to village AOI &bull; Storage: <code>backend/media/satellite/villages/&lt;id&gt;/</code>
            </p>
          </div>
        </div>

        {ingestedScenes.length === 0 ? (
          <div className="empty-library-box">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <circle cx="8.5" cy="8.5" r="1.5"></circle>
              <polyline points="21 15 16 10 5 21"></polyline>
            </svg>
            <p>No Sentinel-2 scenes have been ingested yet for this village.</p>
            <span className="hint-text">Search STAC above and click "Download & Clip AOI" to acquire genuine multispectral bands.</span>
          </div>
        ) : (
          <div className="library-grid-layout">
            {/* Scene Selector List */}
            <div className="scenes-sidebar">
              <span className="sidebar-label">Available Ingested Dates</span>
              <div className="sidebar-scenes-list">
                {ingestedScenes.map((scene) => (
                  <button
                    key={scene.id}
                    type="button"
                    className={`btn-sidebar-scene ${selectedSceneForInspection?.id === scene.id ? 'active' : ''}`}
                    onClick={() => setSelectedSceneForInspection(scene)}
                  >
                    <div className="sidebar-scene-top">
                      <span className="sidebar-scene-date">
                        {new Date(scene.acquisition_date).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        })}
                      </span>
                      <span className="sidebar-scene-bands">{scene.bands_count || scene.bands?.length || 7} Bands</span>
                    </div>
                    <span className="sidebar-scene-id">{scene.scene_id}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Selected Scene Band Table & Metadata */}
            {selectedSceneForInspection && (
              <div className="scene-details-card">
                <div className="scene-meta-banner">
                  <div className="meta-banner-top">
                    <span className="badge-provider">{selectedSceneForInspection.provider}</span>
                    <span className="badge-level">{selectedSceneForInspection.processing_level}</span>
                    {selectedSceneForInspection.aoi_cloud_cover != null && (
                      <span className="badge-aoi-cloud">
                        AOI Cloud: {selectedSceneForInspection.aoi_cloud_cover}% (SCL Validated)
                      </span>
                    )}
                  </div>
                  <h4 className="meta-scene-title">{selectedSceneForInspection.scene_id}</h4>
                  <p className="meta-scene-desc">
                    Acquisition Time: <strong>{new Date(selectedSceneForInspection.acquisition_date).toUTCString()}</strong> &bull; Scene Cloud: {selectedSceneForInspection.cloud_cover}%
                  </p>
                </div>

                <div className="bands-grid-table">
                  <table className="bands-table">
                    <thead>
                      <tr>
                        <th>Band</th>
                        <th>Spectral Description</th>
                        <th>Resolution</th>
                        <th>Projected CRS</th>
                        <th>Dimensions</th>
                        <th>File Size</th>
                        <th>GeoTIFF Asset</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(selectedSceneForInspection.bands || []).map((b) => (
                        <tr key={b.id || b.band_name}>
                          <td className="cell-band-name">
                            <span className="band-code-pill">{b.band_name}</span>
                          </td>
                          <td className="cell-band-desc">
                            {b.band_name === 'B02' && 'Blue (490 nm)'}
                            {b.band_name === 'B03' && 'Green (560 nm)'}
                            {b.band_name === 'B04' && 'Red (665 nm)'}
                            {b.band_name === 'B08' && 'Near Infrared / NIR (842 nm)'}
                            {b.band_name === 'B11' && 'Shortwave Infrared 1 / SWIR 1 (1610 nm)'}
                            {b.band_name === 'B12' && 'Shortwave Infrared 2 / SWIR 2 (2190 nm)'}
                            {b.band_name === 'SCL' && 'Scene Classification Layer (Cloud & Shadow Mask)'}
                          </td>
                          <td>{b.resolution}m</td>
                          <td>
                            <code className="crs-code">{b.crs?.split('[')?.[0] || 'EPSG:32643'}</code>
                          </td>
                          <td>
                            {b.width && b.height ? `${b.width} × ${b.height} px` : 'Clipped AOI'}
                          </td>
                          <td>{b.file_size_formatted || `${Math.round(b.file_size / 1024)} KB`}</td>
                          <td>
                            <a
                              href={b.download_url}
                              target="_blank"
                              rel="noreferrer"
                              className="btn-download-geotiff"
                            >
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="7 10 12 15 17 10"></polyline>
                                <line x1="12" y1="15" x2="12" y2="3"></line>
                              </svg>
                              Download .TIF
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export default SatelliteAcquisition;
