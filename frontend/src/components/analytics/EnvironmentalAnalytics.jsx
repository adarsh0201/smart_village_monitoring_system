import React, { useState, useEffect, useMemo } from 'react';
import {
  Activity,
  Leaf,
  Droplet,
  Sun,
  Layers,
  AlertCircle,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  Download,
  Sliders,
  FileDown,
  Sparkles,
  MapPin,
  Satellite,
} from 'lucide-react';
import { getSceneIndices, computeSceneIndices } from '../../services/api';
import LulcAnalyticsDashboard from './LulcAnalyticsDashboard';

const isOpticalSentinel2Scene = (scene) => {
  if (!scene) return false;
  const sceneId = (scene.scene_id || '').toUpperCase();
  const collection = (scene.collection || '').toLowerCase();

  // Strictly Sentinel-2 optical scenes (S2A or S2B)
  const isS2 =
    sceneId.includes('S2A') ||
    sceneId.includes('S2B') ||
    collection.includes('sentinel-2') ||
    collection.includes('s2');
  // Exclude radar / Sentinel-1
  const isS1 =
    sceneId.includes('S1A') ||
    sceneId.includes('S1B') ||
    sceneId.includes('S1D') ||
    collection.includes('sentinel-1') ||
    collection.includes('sar');

  return isS2 && !isS1;
};

export function EnvironmentalAnalytics({
  villages = [],
  selectedVillage = null,
  onSelectVillage = () => {},
  scenes = [],
  onNavigateToSatellite = () => {},
  onNavigateToGis = null,
  initialIndex = 'ndvi',
}) {
  const [selectedIndex, setSelectedIndex] = useState(initialIndex);
  const [selectedSceneId, setSelectedSceneId] = useState('');
  const [indicesState, setIndicesState] = useState({ sceneId: '', data: [] });
  const [isComputing, setIsComputing] = useState(false);
  const [computeMessage, setComputeMessage] = useState(null);
  const [overlayOpacity, setOverlayOpacity] = useState(90);
  const [maskClouds, setMaskClouds] = useState(true);

  const targetVillageId = selectedVillage?.id ?? (villages[0]?.id ?? '');
  const activeVillageObj =
    villages.find((v) => String(v.id) === String(targetVillageId)) || villages[0];

  // Strictly filter scenes belonging to the active village that are Sentinel-2 optical granules
  const villageScenes = useMemo(
    () =>
      scenes.filter(
        (s) =>
          String(s.village) === String(targetVillageId) &&
          isOpticalSentinel2Scene(s)
      ),
    [scenes, targetVillageId]
  );

  // Derive active scene ID cleanly without cascading setState in an effect
  const activeSceneId = useMemo(() => {
    if (villageScenes.length === 0) return '';
    const exists = villageScenes.some((s) => String(s.id) === String(selectedSceneId));
    return exists ? selectedSceneId : String(villageScenes[0].id);
  }, [villageScenes, selectedSceneId]);

  const indicesData = useMemo(
    () => (activeSceneId && indicesState.sceneId === activeSceneId ? indicesState.data : []),
    [activeSceneId, indicesState]
  );
  const [loadedSceneId, setLoadedSceneId] = useState('');
  const loadingIndices = Boolean(activeSceneId) && loadedSceneId !== activeSceneId;

  // Fetch computed indices whenever activeSceneId changes
  useEffect(() => {
    if (!activeSceneId) {
      return;
    }
    let isCurrent = true;
    getSceneIndices(activeSceneId)
      .then((data) => {
        if (isCurrent) {
          setIndicesState({
            sceneId: activeSceneId,
            data: Array.isArray(data) ? data : [],
          });
          setLoadedSceneId(activeSceneId);
        }
      })
      .catch(() => {
        if (isCurrent) {
          setIndicesState({ sceneId: activeSceneId, data: [] });
          setLoadedSceneId(activeSceneId);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [activeSceneId]);

  // Handle on-demand calculation or re-computation
  const handleComputeIndices = async (overwrite = false) => {
    if (!activeSceneId) return;
    setIsComputing(true);
    setComputeMessage(null);
    try {
      const res = await computeSceneIndices(activeSceneId, {
        mask_clouds: maskClouds,
        overwrite: overwrite,
      });
      if (res?.indices) {
        setIndicesState({ sceneId: activeSceneId, data: res.indices });
        setLoadedSceneId(activeSceneId);
        setComputeMessage({
          type: 'success',
          text: res.message || 'All 4 spectral indices successfully calculated and rendered.',
        });
      }
    } catch (err) {
      setComputeMessage({
        type: 'error',
        text: err?.response?.data?.error || err.message || 'Failed to compute spectral indices.',
      });
    } finally {
      setIsComputing(false);
    }
  };

  const activeSceneObj = villageScenes.find((s) => String(s.id) === String(activeSceneId));

  const indices = [
    {
      id: 'ndvi',
      name: 'NDVI — Normalized Difference Vegetation Index',
      shortName: 'NDVI',
      formula: '(B08 - B04) / (B08 + B04)',
      bands: [
        { code: 'B08', name: 'Near Infrared (NIR, 842nm)', role: 'Reflected strongly by healthy plant mesophyll' },
        { code: 'B04', name: 'Red (665nm)', role: 'Absorbed by chlorophyll pigments for photosynthesis' },
      ],
      icon: Leaf,
      color: '#4A7C59',
      range: '[-1.0 to +1.0]',
      colormapName: 'RdYlGn (Red-Yellow-Green)',
      colormapGradient:
        'linear-gradient(to right, #a50026, #d73027, #f46d43, #fdae61, #fee08b, #d9ef8b, #a6d96a, #66bd63, #1a9850, #006837)',
      legendLabels: [
        '-0.2 (Water/Barren)',
        '0.0 (Soil)',
        '+0.25 (Scrub)',
        '+0.50 (Cropland)',
        '+0.80+ (Dense Canopy)',
      ],
      purpose:
        'Quantifies photosynthetic biomass density, canopy vigour, and moisture stress across village agricultural plots.',
      rajasthanContext:
        'Critical for tracking Kharif/Rabi crop stages and survival rates of village social forestry plantations (such as Piplantri watershed afforestation).',
    },
    {
      id: 'ndwi',
      name: 'NDWI — Normalized Difference Water Index (McFeeters)',
      shortName: 'NDWI',
      formula: '(B03 - B08) / (B03 + B08)',
      bands: [
        { code: 'B03', name: 'Green (560nm)', role: 'High reflectance of open water features' },
        { code: 'B08', name: 'Near Infrared (NIR, 842nm)', role: 'Strong absorption by clear surface water' },
      ],
      icon: Droplet,
      color: '#346078',
      range: '[-1.0 to +1.0]',
      colormapName: 'Blues (Water Depth/Purity)',
      colormapGradient:
        'linear-gradient(to right, #ffffd4, #fed98e, #fe9929, #d95f0e, #993404, #7fcdbb, #41b6c4, #1d91c0, #225ea8, #0c2c84)',
      legendLabels: [
        '-0.5 (Dry Soil)',
        '-0.2 (Moist Soil)',
        '0.0 (Shoreline)',
        '+0.2 (Shallow Pond)',
        '+0.5+ (Deep Reservoir)',
      ],
      purpose:
        'Delineates open surface water bodies, irrigation tanks, johads, and village talabs while suppressing dry soil background.',
      rajasthanContext:
        'Essential for measuring seasonal water retention dynamics in traditional rainwater harvesting structures (Johads, Check Dams, and Talabs).',
    },
    {
      id: 'savi',
      name: 'SAVI — Soil-Adjusted Vegetation Index (Huete)',
      shortName: 'SAVI',
      formula: '((B08 - B04) / (B08 + B04 + 0.5)) * 1.5',
      bands: [
        { code: 'B08', name: 'Near Infrared (NIR, 842nm)', role: 'Canopy cellular reflectance' },
        { code: 'B04', name: 'Red (665nm)', role: 'Chlorophyll absorption' },
        { code: 'L=0.5', name: 'Soil Brightness Correction', role: 'Calibrates for high ground soil albedo' },
      ],
      icon: Sun,
      color: '#8F641B',
      range: '[-1.0 to +1.0]',
      colormapName: 'YlGn (Yellow-Green with Soil Shift)',
      colormapGradient: 'linear-gradient(to right, #8c510a, #d8b365, #f6e8c3, #c7eae5, #5ab4ac, #01665e)',
      legendLabels: [
        '-0.1 (Water)',
        '0.0 (Sandy Soil)',
        '+0.15 (Arid Pasture)',
        '+0.40 (Crop Cover)',
        '+0.70+ (Dense Canopy)',
      ],
      purpose:
        'Suppresses bare ground optical reflectance in arid, semi-arid, or low-density canopy zones using empirical soil brightness factor L=0.5.',
      rajasthanContext:
        'Calibrated specifically for semi-arid and desert terrain (e.g., Bhadla, Jodhpur, Thar regions) where bright sandy soil distorts standard NDVI values.',
    },
    {
      id: 'mndwi',
      name: 'MNDWI — Modified Normalized Difference Water Index (Xu)',
      shortName: 'MNDWI',
      formula: '(B03 - B11) / (B03 + B11)',
      bands: [
        { code: 'B03', name: 'Green (560nm)', role: 'High reflectance of water' },
        { code: 'B11', name: 'SWIR 1 (1610nm, resampled 10m)', role: 'Absorbed by water, reflected by built structures & stone' },
      ],
      icon: Activity,
      color: '#346078',
      range: '[-1.0 to +1.0]',
      colormapName: 'Blues / Cyan (Built Suppression)',
      colormapGradient:
        'linear-gradient(to right, #f7fcf0, #e0f3db, #ccebc5, #a8ddb5, #7bccc4, #4eb3d3, #2b8cbe, #0868ac, #084081)',
      legendLabels: [
        '-0.5 (Built/Stone/Soil)',
        '-0.2 (Dry Soil)',
        '0.0 (Water Edge)',
        '+0.2 (Turbid Water)',
        '+0.5+ (Clear Reservoir)',
      ],
      purpose:
        'Removes false positives from village rooftops, paved roads, and rocky terrain while sharply delineating surface water boundaries.',
      rajasthanContext:
        'Effectively separates village settlement rooftops and stone quarry areas from ephemeral post-monsoon tanks in rural watersheds.',
    },
    {
      id: 'lulc',
      name: 'AI Land Use & Land Cover (LULC) Classification',
      shortName: 'AI Land Cover',
      formula: 'Random Forest 6-Feature Fusion [VV, VH, Elev, Slope, NDVI, NDWI]',
      icon: Sparkles,
      color: '#4A7C59',
      isLulc: true,
    },
  ];

  const currentIndex = indices.find((i) => i.id === selectedIndex) || indices[0];
  const CurrentIndexIcon = currentIndex.icon;

  // Find calculated record in database for the active index type
  const activeRecord = indicesData.find(
    (item) => item.index_type?.toUpperCase() === currentIndex.shortName.toUpperCase()
  );

  const hasIndices = indicesData.length > 0;

  return (
    <div className="environmental-analytics-workspace">
      {/* Section 1: Institutional Report Header & Control Selection */}
      <section className="report-section" aria-labelledby="analytics-page-title">
        <div
          className="page-header"
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-start',
            gap: '18px',
          }}
        >
          <div className="page-header-title-block">
            <span className="report-kicker">Remote Sensing & Bio-Physical Report</span>
            <h1 id="analytics-page-title" className="page-title">
              Environmental Analytics & Spectral Indices
            </h1>
            <p className="page-subtitle">
              Bio-physical vegetation and hydrological indicators derived from Sentinel-2 Level-2A surface reflectance rasters
            </p>
          </div>

          {/* Village and Scene Selectors — strictly pinned left at all times */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-start',
              gap: '18px',
              flexWrap: 'wrap',
              width: '100%',
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              padding: '14px 18px',
              boxShadow: 'var(--shadow-xs)',
            }}
          >
            {/* Village Selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <label
                htmlFor="analytics-village-select"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '13px',
                  fontWeight: 700,
                  color: 'var(--color-text-secondary)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.03em',
                }}
              >
                <MapPin size={15} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
                <span>Village:</span>
              </label>
              <select
                id="analytics-village-select"
                className="form-select"
                value={targetVillageId}
                onChange={(e) => {
                  const found = villages.find((v) => String(v.id) === String(e.target.value));
                  if (found) onSelectVillage(found);
                }}
                style={{ minWidth: '230px', width: 'auto' }}
              >
                {villages.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name} ({v.district})
                  </option>
                ))}
              </select>
            </div>

            {/* Scene Selector (Strictly Optical Sentinel-2) */}
            {villageScenes.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <label
                  htmlFor="analytics-scene-select"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '13px',
                    fontWeight: 700,
                    color: 'var(--color-text-secondary)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.03em',
                  }}
                >
                  <Satellite size={15} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
                  <span>Sentinel-2 Scene:</span>
                </label>
                <select
                  id="analytics-scene-select"
                  className="form-select"
                  value={activeSceneId}
                  onChange={(e) => setSelectedSceneId(e.target.value)}
                  style={{
                    minWidth: '280px',
                    width: 'auto',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '13.5px',
                  }}
                >
                  {villageScenes.map((s) => (
                    <option key={s.id} value={s.id}>
                      {new Date(s.acquisition_date).toLocaleDateString()} — {s.scene_id.substring(0, 24)}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Operational Status Notice */}
        <div
          className="alert-banner alert-success"
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '14px',
            marginBottom: '22px',
          }}
        >
          <CheckCircle2 size={20} style={{ flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
          <div style={{ flex: 1 }}>
            <strong style={{ display: 'block', fontSize: '15px', color: 'var(--color-primary-dark)', marginBottom: 4 }}>
              Environmental Analytics Engine: Verified Operational Status
            </strong>
            <span style={{ fontSize: '14px', color: 'var(--color-text-primary)', lineHeight: 1.6 }}>
              Float32 raster computation is active for optical Level-2A reflectance observations with Scene Classification Layer (SCL) cloud and shadow masking enabled.
            </span>
          </div>
        </div>

        {/* Compute Feedback Banner */}
        {computeMessage && (
          <div
            className={`alert-banner ${computeMessage.type === 'error' ? 'alert-danger' : 'alert-success'}`}
            style={{ marginBottom: '20px' }}
          >
            {computeMessage.type === 'error' ? (
              <AlertCircle size={18} aria-hidden="true" />
            ) : (
              <CheckCircle2 size={18} aria-hidden="true" />
            )}
            <span>{computeMessage.text}</span>
          </div>
        )}

        {/* Index Selector Tabs */}
        <div className="tab-navigation" role="tablist" aria-label="Environmental Analysis Modes">
          {indices.map((idx) => {
            const Icon = idx.icon;
            const isComputed = indicesData.some(
              (item) => item.index_type?.toUpperCase() === idx.shortName.toUpperCase()
            );
            const isSelected = selectedIndex === idx.id;
            return (
              <button
                key={idx.id}
                type="button"
                role="tab"
                aria-selected={isSelected}
                className={`tab-btn ${isSelected ? 'active' : ''}`}
                onClick={() => setSelectedIndex(idx.id)}
              >
                <Icon
                  size={16}
                  style={{ color: isSelected ? idx.color : 'inherit' }}
                  aria-hidden="true"
                />
                <span>{idx.shortName}</span>
                {isComputed && (
                  <span
                    className="badge badge-green"
                    style={{ fontSize: '11px', padding: '1px 7px' }}
                  >
                    Ready
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </section>

      {/* Conditional: AI LULC Classification Dashboard vs. Spectral Indices */}
      {selectedIndex === 'lulc' ? (
        <LulcAnalyticsDashboard
          villageId={targetVillageId}
          villageName={activeVillageObj?.name || 'Village'}
          onNavigateToGis={onNavigateToGis || onNavigateToSatellite}
        />
      ) : (
        <>
          {/* Section 2: Quantitative Bio-Physical Telemetry */}
          <section className="report-section" aria-labelledby="telemetry-section-heading">
            <div className="report-section-header">
              <div>
                <h2 id="telemetry-section-heading" className="report-section-title">
                  1. Quantitative Telemetry & Pixel Audit ({currentIndex.shortName})
                </h2>
                <p className="report-section-subtitle">
                  Statistical summary across unmasked agricultural and watershed grid cells in{' '}
                  <strong>{activeVillageObj?.name || 'Selected Village'}</strong>
                </p>
              </div>
              <span className="badge badge-gray">Grid Resolution: 10m &times; 10m</span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '16px',
              }}
            >
              {/* Metric 1: Mean Value */}
              <div className="card" style={{ padding: '18px 20px', marginBottom: 0 }}>
                <span className="kpi-label">Mean {currentIndex.shortName}</span>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginTop: '8px', flexWrap: 'wrap' }}>
                  <span
                    style={{
                      fontSize: '28px',
                      fontWeight: 700,
                      color: 'var(--color-text-primary)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {activeRecord?.mean !== undefined && activeRecord?.mean !== null
                      ? activeRecord.mean > 0
                        ? `+${activeRecord.mean.toFixed(4)}`
                        : activeRecord.mean.toFixed(4)
                      : '—'}
                  </span>
                  {activeRecord?.mean !== undefined && activeRecord?.mean !== null && (
                    <span
                      className={`badge ${
                        activeRecord.mean > 0.25
                          ? 'badge-green'
                          : activeRecord.mean > 0.1
                            ? 'badge-warning'
                            : 'badge-gray'
                      }`}
                    >
                      {currentIndex.id === 'ndvi'
                        ? activeRecord.mean > 0.3
                          ? 'Good Canopy'
                          : activeRecord.mean > 0.15
                            ? 'Sparse Scrub'
                            : 'Arid / Barren'
                        : 'Verified Mean'}
                    </span>
                  )}
                </div>
                <span className="kpi-subtext" style={{ marginTop: '6px', display: 'block' }}>
                  Unmasked pixel average
                </span>
              </div>

              {/* Metric 2: Median Value */}
              <div className="card" style={{ padding: '18px 20px', marginBottom: 0 }}>
                <span className="kpi-label">Median {currentIndex.shortName}</span>
                <div style={{ marginTop: '8px' }}>
                  <span
                    style={{
                      fontSize: '28px',
                      fontWeight: 700,
                      color: 'var(--color-text-primary)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {activeRecord?.median !== undefined && activeRecord?.median !== null
                      ? activeRecord.median > 0
                        ? `+${activeRecord.median.toFixed(4)}`
                        : activeRecord.median.toFixed(4)
                      : '—'}
                  </span>
                </div>
                <span className="kpi-subtext" style={{ marginTop: '6px', display: 'block' }}>
                  50th percentile distribution
                </span>
              </div>

              {/* Metric 3: Dynamic Physical Range */}
              <div className="card" style={{ padding: '18px 20px', marginBottom: 0 }}>
                <span className="kpi-label">Observed Min / Max Range</span>
                <div
                  style={{
                    marginTop: '10px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '17px',
                    fontWeight: 700,
                    color: 'var(--color-text-primary)',
                  }}
                >
                  {activeRecord?.min_value !== undefined && activeRecord?.min_value !== null
                    ? `[${activeRecord.min_value.toFixed(4)} to ${activeRecord.max_value?.toFixed(4)}]`
                    : '—'}
                </div>
                <span className="kpi-subtext" style={{ marginTop: '8px', display: 'block' }}>
                  Physical boundary: {currentIndex.range}
                </span>
              </div>

              {/* Metric 4: Standard Deviation */}
              <div className="card" style={{ padding: '18px 20px', marginBottom: 0 }}>
                <span className="kpi-label">Standard Deviation (&sigma;)</span>
                <div
                  style={{
                    marginTop: '8px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '28px',
                    fontWeight: 700,
                    color: 'var(--color-text-primary)',
                  }}
                >
                  {activeRecord?.std_dev !== undefined && activeRecord?.std_dev !== null
                    ? `±${activeRecord.std_dev.toFixed(4)}`
                    : '—'}
                </div>
                <span className="kpi-subtext" style={{ marginTop: '6px', display: 'block' }}>
                  Spatial heterogeneity index
                </span>
              </div>

              {/* Metric 5: Pixel & Cloud Masking Audit */}
              <div className="card" style={{ padding: '18px 20px', marginBottom: 0 }}>
                <span className="kpi-label">Valid Pixels &amp; Cloud Audit</span>
                <div
                  style={{
                    marginTop: '10px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '18px',
                    fontWeight: 700,
                    color: 'var(--color-text-primary)',
                  }}
                >
                  {activeRecord?.valid_pixel_count !== undefined
                    ? `${activeRecord.valid_pixel_count.toLocaleString()} px`
                    : '—'}
                </div>
                <span className="kpi-subtext" style={{ marginTop: '6px', display: 'block' }}>
                  {activeRecord?.cloud_pixel_count !== undefined
                    ? `${activeRecord.cloud_pixel_count} cloud px masked (${
                        activeRecord.total_pixel_count
                          ? ((activeRecord.cloud_pixel_count / activeRecord.total_pixel_count) * 100).toFixed(2)
                          : 0
                      }%)`
                    : 'SCL cloud masking ready'}
                </span>
              </div>
            </div>
          </section>

          {/* Section 3: Spatial Raster Plate Visualization */}
          <section className="report-section" aria-labelledby="raster-plate-heading">
            <div className="report-section-header">
              <div>
                <h2 id="raster-plate-heading" className="report-section-title">
                  2. Spatial Raster Plate Visualization — {currentIndex.shortName}
                </h2>
                <p className="report-section-subtitle">
                  Clipped 10m GeoTIFF map output and export actions for{' '}
                  <strong>{activeVillageObj?.name || 'Village'}</strong>
                </p>
              </div>
            </div>

            <div className="card" style={{ marginBottom: 0 }}>
              <div className="card-header">
                <div className="card-title-group">
                  <h3 className="card-title">
                    <Activity size={18} style={{ color: currentIndex.color }} aria-hidden="true" />
                    <span>{currentIndex.shortName} Cartographic Overlay</span>
                  </h3>
                  <p className="card-subtitle">
                    Granule:{' '}
                    <code className="cell-code">{activeSceneObj?.scene_id || 'No Scene Selected'}</code>
                  </p>
                </div>

                {/* Action Toolbar — Every icon always accompanied by explicit text label */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                  {/* Cloud Mask Toggle */}
                  <label
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '7px',
                      fontSize: '14px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      color: 'var(--color-text-primary)',
                      padding: '6px 10px',
                      background: 'var(--color-surface-muted)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm)',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={maskClouds}
                      onChange={(e) => setMaskClouds(e.target.checked)}
                      style={{ cursor: 'pointer', accentColor: 'var(--color-primary)', width: 16, height: 16 }}
                    />
                    <span>SCL Cloud Masking</span>
                  </label>

                  {/* Opacity Slider with explicit text label */}
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '6px 12px',
                      background: 'var(--color-surface-muted)',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm)',
                    }}
                  >
                    <Sliders size={15} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
                    <label
                      htmlFor="raster-opacity-slider"
                      style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--color-text-secondary)' }}
                    >
                      Opacity:
                    </label>
                    <input
                      id="raster-opacity-slider"
                      type="range"
                      min="20"
                      max="100"
                      value={overlayOpacity}
                      onChange={(e) => setOverlayOpacity(Number(e.target.value))}
                      style={{ width: '85px', cursor: 'pointer', accentColor: 'var(--color-primary)' }}
                    />
                    <span
                      style={{
                        fontSize: '13px',
                        fontWeight: 700,
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--color-text-primary)',
                        minWidth: '38px',
                      }}
                    >
                      {overlayOpacity}%
                    </span>
                  </div>

                  {/* Compute / Recompute Button */}
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => handleComputeIndices(hasIndices)}
                    disabled={isComputing || !activeSceneId}
                  >
                    <RefreshCw size={15} className={isComputing ? 'animate-spin' : ''} aria-hidden="true" />
                    <span>
                      {isComputing
                        ? 'Calculating Rasters...'
                        : hasIndices
                          ? 'Recompute All Indices'
                          : 'Compute Spectral Indices'}
                    </span>
                  </button>

                  {/* Download GeoTIFF Button */}
                  {activeRecord?.download_url && (
                    <a
                      href={activeRecord.download_url}
                      download
                      className="btn btn-secondary btn-sm"
                      title="Download 32-bit floating point GeoTIFF"
                    >
                      <Download size={15} aria-hidden="true" />
                      <span>Download GeoTIFF (.tif)</span>
                    </a>
                  )}

                  {/* Download PNG Overlay */}
                  {activeRecord?.png_url && (
                    <a
                      href={activeRecord.png_url}
                      download
                      className="btn btn-secondary btn-sm"
                      title="Download transparent RGBA PNG overlay"
                    >
                      <FileDown size={15} aria-hidden="true" />
                      <span>Download Map PNG</span>
                    </a>
                  )}
                </div>
              </div>

              {/* Paper-Light Cartographic Plate Frame */}
              <div
                style={{
                  position: 'relative',
                  minHeight: '380px',
                  maxHeight: '540px',
                  backgroundColor: 'var(--color-surface-muted)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md)',
                  overflow: 'hidden',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '28px',
                }}
              >
                {loadingIndices || isComputing ? (
                  <div style={{ textAlign: 'center', color: 'var(--color-text-primary)' }}>
                    <RefreshCw
                      size={36}
                      className="animate-spin"
                      style={{ color: 'var(--color-primary)', marginBottom: 12 }}
                      aria-hidden="true"
                    />
                    <h4 style={{ margin: '0 0 6px 0', fontSize: '17px' }}>
                      {isComputing
                        ? 'Processing Sentinel-2 Surface Reflectance Rasters...'
                        : 'Loading Spectral Indices...'}
                    </h4>
                    <p style={{ margin: 0, fontSize: '14px', color: 'var(--color-text-secondary)' }}>
                      Calculating pixel arrays with Rasterio &amp; NumPy
                    </p>
                  </div>
                ) : activeRecord?.png_url ? (
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: '100%',
                      gap: '12px',
                    }}
                  >
                    <div
                      style={{
                        border: '1px solid var(--color-border-dark)',
                        borderRadius: 'var(--radius-sm)',
                        boxShadow: 'var(--shadow-md)',
                        maxWidth: '100%',
                        maxHeight: '420px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        backgroundColor: 'var(--color-surface)',
                        padding: '8px',
                      }}
                    >
                      <img
                        src={activeRecord.png_url}
                        alt={`${currentIndex.name} Raster Overlay`}
                        style={{
                          display: 'block',
                          maxWidth: '100%',
                          maxHeight: '390px',
                          objectFit: 'contain',
                          opacity: overlayOpacity / 100,
                          transition: 'opacity 0.15s ease',
                        }}
                      />
                    </div>

                    {/* Clean Plate Caption Strip */}
                    <div
                      style={{
                        background: 'var(--color-surface)',
                        color: 'var(--color-text-secondary)',
                        fontSize: '13px',
                        padding: '6px 14px',
                        borderRadius: 'var(--radius-xs)',
                        fontFamily: 'var(--font-mono)',
                        border: '1px solid var(--color-border)',
                      }}
                    >
                      Plate Metadata: {activeRecord.resolution}m Ground Sample Distance &bull;{' '}
                      {activeRecord.crs} &bull; Float32 GeoTIFF
                    </div>
                  </div>
                ) : villageScenes.length === 0 ? (
                  <div style={{ textAlign: 'center', color: 'var(--color-text-primary)', maxWidth: '460px' }}>
                    <AlertCircle
                      size={36}
                      style={{ color: 'var(--color-warning)', marginBottom: 12 }}
                      aria-hidden="true"
                    />
                    <h4 style={{ margin: '0 0 8px 0', fontSize: '17px' }}>
                      No Optical Sentinel-2 Imagery Ingested
                    </h4>
                    <p style={{ margin: 0, fontSize: '14px', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                      Acquire Sentinel-2 multispectral scenes for {activeVillageObj?.name} in the Satellite Imagery workspace before computing spectral indices.
                    </p>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={onNavigateToSatellite}
                      style={{ marginTop: '18px' }}
                    >
                      <span>Go to Satellite Acquisition</span>
                      <ArrowRight size={15} aria-hidden="true" />
                    </button>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', color: 'var(--color-text-primary)', maxWidth: '460px' }}>
                    <Activity
                      size={36}
                      style={{ color: 'var(--color-primary)', marginBottom: 12 }}
                      aria-hidden="true"
                    />
                    <h4 style={{ margin: '0 0 8px 0', fontSize: '17px' }}>
                      Spectral Indices Ready to Calculate
                    </h4>
                    <p style={{ margin: 0, fontSize: '14px', color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                      Sentinel-2 Level-2A input bands are ingested and verified on disk. Select below to compute NDVI, NDWI, SAVI, and MNDWI rasters.
                    </p>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => handleComputeIndices(false)}
                      disabled={isComputing}
                      style={{ marginTop: '18px' }}
                    >
                      <RefreshCw size={15} aria-hidden="true" />
                      <span>Compute All 4 Spectral Indices</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Cartographic Colormap Scale Legend */}
              <div
                style={{
                  marginTop: '18px',
                  padding: '14px 16px',
                  background: 'var(--color-surface-muted)',
                  border: '1px solid var(--color-border-light)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: 8,
                    flexWrap: 'wrap',
                    gap: '8px',
                  }}
                >
                  <span
                    style={{
                      fontSize: '13px',
                      fontWeight: 700,
                      color: 'var(--color-text-secondary)',
                      textTransform: 'uppercase',
                    }}
                  >
                    Cartographic Scale: {currentIndex.colormapName}
                  </span>
                  <span
                    style={{
                      fontSize: '13px',
                      color: 'var(--color-text-secondary)',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    Physical Range: {currentIndex.range}
                  </span>
                </div>
                <div
                  style={{
                    height: '16px',
                    borderRadius: 'var(--radius-xs)',
                    background: currentIndex.colormapGradient,
                    border: '1px solid var(--color-border-dark)',
                    marginBottom: '8px',
                  }}
                />
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '8px',
                    fontSize: '12.5px',
                    fontWeight: 600,
                    color: 'var(--color-text-secondary)',
                  }}
                >
                  {currentIndex.legendLabels.map((lbl) => (
                    <span key={lbl}>{lbl}</span>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* Section 4: Scientific Methodology & Satellite Input Audit */}
          <section className="report-section" aria-labelledby="methodology-section-heading">
            <div className="report-section-header">
              <div>
                <h2 id="methodology-section-heading" className="report-section-title">
                  3. Scientific Methodology &amp; Satellite Asset Verification
                </h2>
                <p className="report-section-subtitle">
                  Index equation specifications and verified local input rasters
                </p>
              </div>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
                gap: '22px',
              }}
            >
              {/* Panel 1: Scientific & Mathematical Specification */}
              <div className="card" style={{ marginBottom: 0 }}>
                <div className="card-header">
                  <div className="card-title-group">
                    <h3 className="card-title">
                      <CurrentIndexIcon
                        size={18}
                        style={{ color: currentIndex.color }}
                        aria-hidden="true"
                      />
                      <span>{currentIndex.name}</span>
                    </h3>
                    <p className="card-subtitle">Remote sensing bio-physical index formulation</p>
                  </div>
                  <span className="badge badge-gray" style={{ fontFamily: 'var(--font-mono)' }}>
                    Range: {currentIndex.range}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                  {/* Mathematical Formula Presentation */}
                  <div
                    style={{
                      background: 'var(--color-surface-muted)',
                      padding: '18px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-border)',
                      textAlign: 'center',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '12px',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        color: 'var(--color-text-muted)',
                        display: 'block',
                        marginBottom: 8,
                        fontWeight: 700,
                      }}
                    >
                      Mathematical Formulation
                    </span>
                    <code
                      style={{
                        fontSize: '19px',
                        fontWeight: 700,
                        color: 'var(--color-primary-dark)',
                        letterSpacing: '0.02em',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      {currentIndex.formula}
                    </code>
                  </div>

                  {/* Scientific Explanation */}
                  <div>
                    <span
                      style={{
                        fontSize: '12.5px',
                        fontWeight: 700,
                        color: 'var(--color-text-secondary)',
                        textTransform: 'uppercase',
                        display: 'block',
                        marginBottom: 6,
                      }}
                    >
                      Primary Remote Sensing Purpose:
                    </span>
                    <p
                      style={{
                        margin: 0,
                        fontSize: '15px',
                        color: 'var(--color-text-primary)',
                        lineHeight: 1.65,
                      }}
                    >
                      {currentIndex.purpose}
                    </p>
                  </div>

                  {/* Regional Administrative Context */}
                  <div
                    style={{
                      background: 'var(--color-success-bg)',
                      borderLeft: '4px solid var(--color-primary)',
                      padding: '14px 18px',
                      borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                    }}
                  >
                    <span
                      style={{
                        fontSize: '13px',
                        fontWeight: 700,
                        color: 'var(--color-primary-dark)',
                        display: 'block',
                        marginBottom: 4,
                      }}
                    >
                      Administrative &amp; Agro-Climatic Context:
                    </span>
                    <p
                      style={{
                        margin: 0,
                        fontSize: '14px',
                        color: 'var(--color-text-primary)',
                        lineHeight: 1.6,
                      }}
                    >
                      {currentIndex.rajasthanContext}
                    </p>
                  </div>
                </div>
              </div>

              {/* Panel 2: Required Satellite Inputs & Local Availability */}
              <div className="card" style={{ marginBottom: 0 }}>
                <div className="card-header">
                  <div className="card-title-group">
                    <h3 className="card-title">
                      <Layers size={18} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
                      <span>Required Satellite Input Rasters</span>
                    </h3>
                    <p className="card-subtitle">
                      Local Sentinel-2 Level-2A assets for{' '}
                      <strong>{activeVillageObj?.name}</strong>
                    </p>
                  </div>
                  <span className="badge badge-gray">
                    {villageScenes.length} Scene{villageScenes.length !== 1 ? 's' : ''} Available
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                  {/* Required Spectral Bands */}
                  <div>
                    <span
                      style={{
                        fontSize: '12.5px',
                        fontWeight: 700,
                        color: 'var(--color-text-secondary)',
                        textTransform: 'uppercase',
                        display: 'block',
                        marginBottom: 8,
                      }}
                    >
                      Required Sentinel-2 Spectral Bands:
                    </span>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {currentIndex.bands.map((b) => (
                        <div
                          key={b.code}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            gap: '12px',
                            flexWrap: 'wrap',
                            padding: '10px 14px',
                            background: 'var(--color-surface-muted)',
                            border: '1px solid var(--color-border-light)',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '14px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span className="badge badge-green" style={{ fontFamily: 'var(--font-mono)' }}>
                              {b.code}
                            </span>
                            <strong>{b.name}</strong>
                          </div>
                          <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                            {b.role}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Ingested Scenes Status */}
                  <div>
                    <span
                      style={{
                        fontSize: '12.5px',
                        fontWeight: 700,
                        color: 'var(--color-text-secondary)',
                        textTransform: 'uppercase',
                        display: 'block',
                        marginBottom: 8,
                      }}
                    >
                      Ingested Satellite Observations:
                    </span>

                    {villageScenes.length === 0 ? (
                      <div
                        style={{
                          textAlign: 'center',
                          padding: '24px 16px',
                          background: 'var(--color-surface-muted)',
                          borderRadius: 'var(--radius-md)',
                          border: '1px dashed var(--color-border-dark)',
                        }}
                      >
                        <AlertCircle
                          size={28}
                          style={{ color: 'var(--color-warning)', marginBottom: 8 }}
                          aria-hidden="true"
                        />
                        <h4 style={{ margin: '0 0 6px 0', fontSize: '15px', color: 'var(--color-text-primary)' }}>
                          No Ingested Scenes For This Village
                        </h4>
                        <p style={{ margin: 0, fontSize: '14px', color: 'var(--color-text-secondary)' }}>
                          Acquire Sentinel-2 scenes for {activeVillageObj?.name} in the Satellite Imagery workspace.
                        </p>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={onNavigateToSatellite}
                          style={{ marginTop: '14px' }}
                        >
                          <span>Go to Acquisition Pipeline</span>
                          <ArrowRight size={15} aria-hidden="true" />
                        </button>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {villageScenes.map((scene) => {
                          const isSelected = String(scene.id) === String(activeSceneId);
                          return (
                            <button
                              key={scene.id}
                              type="button"
                              style={{
                                width: '100%',
                                textAlign: 'left',
                                padding: '12px 16px',
                                background: isSelected
                                  ? 'var(--color-success-bg)'
                                  : 'var(--color-surface)',
                                border: isSelected
                                  ? '1px solid var(--color-primary)'
                                  : '1px solid var(--color-border)',
                                borderRadius: 'var(--radius-sm)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                flexWrap: 'wrap',
                                gap: '10px',
                                cursor: 'pointer',
                                transition: 'all var(--transition-fast)',
                              }}
                              onClick={() => setSelectedSceneId(String(scene.id))}
                            >
                              <div>
                                <span
                                  style={{
                                    fontFamily: 'var(--font-mono)',
                                    fontWeight: 700,
                                    fontSize: '13.5px',
                                    display: 'block',
                                    color: 'var(--color-text-primary)',
                                  }}
                                >
                                  {scene.scene_id}
                                </span>
                                <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                                  Acquired: {new Date(scene.acquisition_date).toLocaleDateString()} &bull; Cloud:{' '}
                                  {scene.cloud_cover}% &bull; {scene.bands_count || 7} Bands
                                </span>
                              </div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span className="badge badge-green">
                                  <ShieldCheck size={13} aria-hidden="true" />
                                  <span>Rasters Ingested</span>
                                </span>
                                {isSelected && (
                                  <span className="badge badge-green" style={{ fontWeight: 700 }}>
                                    Active Selection
                                  </span>
                                )}
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

export default EnvironmentalAnalytics;
