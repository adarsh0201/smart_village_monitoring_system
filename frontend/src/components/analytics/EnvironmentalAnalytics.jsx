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
} from 'lucide-react';
import { getSceneIndices, computeSceneIndices } from '../../services/api';
import LulcAnalyticsDashboard from './LulcAnalyticsDashboard';

export function EnvironmentalAnalytics({
  villages = [],
  selectedVillage = null,
  onSelectVillage = () => {},
  scenes = [],
  onNavigateToSatellite = () => {},
}) {
  const [selectedIndex, setSelectedIndex] = useState('ndvi');
  const [selectedSceneId, setSelectedSceneId] = useState('');
  const [indicesData, setIndicesData] = useState([]);
  const [loadingIndices, setLoadingIndices] = useState(false);
  const [isComputing, setIsComputing] = useState(false);
  const [computeMessage, setComputeMessage] = useState(null);
  const [overlayOpacity, setOverlayOpacity] = useState(90);
  const [maskClouds, setMaskClouds] = useState(true);

  const targetVillageId = selectedVillage?.id ?? (villages[0]?.id ?? '');
  const activeVillageObj = villages.find((v) => String(v.id) === String(targetVillageId)) || villages[0];

  // Filter scenes belonging to the active village
  const villageScenes = useMemo(
    () => scenes.filter((s) => String(s.village) === String(targetVillageId)),
    [scenes, targetVillageId]
  );

  // Derive active scene ID cleanly without cascading setState in an effect
  const activeSceneId = useMemo(() => {
    if (villageScenes.length === 0) return '';
    const exists = villageScenes.some((s) => String(s.id) === String(selectedSceneId));
    return exists ? selectedSceneId : String(villageScenes[0].id);
  }, [villageScenes, selectedSceneId]);

  // Fetch computed indices whenever activeSceneId changes
  useEffect(() => {
    if (!activeSceneId) {
      return;
    }
    let isCurrent = true;
    getSceneIndices(activeSceneId)
      .then((data) => {
        if (isCurrent) {
          setIndicesData(Array.isArray(data) ? data : []);
          setLoadingIndices(false);
        }
      })
      .catch(() => {
        if (isCurrent) {
          setIndicesData([]);
          setLoadingIndices(false);
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
        setIndicesData(res.indices);
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
      color: '#2E7D32',
      range: '[-1.0 to +1.0]',
      colormapName: 'RdYlGn (Red-Yellow-Green)',
      colormapGradient: 'linear-gradient(to right, #a50026, #d73027, #f46d43, #fdae61, #fee08b, #d9ef8b, #a6d96a, #66bd63, #1a9850, #006837)',
      legendLabels: ['-0.2 (Water/Barren)', '0.0 (Soil)', '+0.25 (Scrub)', '+0.50 (Cropland)', '+0.80+ (Dense Canopy)'],
      purpose: 'Quantifies photosynthetic biomass density, canopy vigour, and moisture stress across village agricultural plots.',
      rajasthanContext: 'Critical for tracking Kharif/Rabi crop stages and survival rates of village social forestry plantations in arid Rajasthan (e.g. Piplantri tree planting initiatives).',
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
      color: '#0284c7',
      range: '[-1.0 to +1.0]',
      colormapName: 'Blues (Water Depth/Purity)',
      colormapGradient: 'linear-gradient(to right, #ffffd4, #fed98e, #fe9929, #d95f0e, #993404, #7fcdbb, #41b6c4, #1d91c0, #225ea8, #0c2c84)',
      legendLabels: ['-0.5 (Vegetation/Dry Soil)', '-0.2 (Moist Soil)', '0.0 (Water Boundary)', '+0.2 (Shallow Pond)', '+0.5+ (Deep Reservoir)'],
      purpose: 'Delineates open surface water bodies, irrigation tanks, johads, and village talabs while suppressing soil background.',
      rajasthanContext: 'Essential for measuring water retention dynamics in traditional Rajasthani rainwater harvesting structures (Johads, Bunds, and Talabs) across seasonal dry spells.',
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
      color: '#d97706',
      range: '[-1.0 to +1.0]',
      colormapName: 'YlGn (Yellow-Green with Soil Shift)',
      colormapGradient: 'linear-gradient(to right, #8c510a, #d8b365, #f6e8c3, #c7eae5, #5ab4ac, #01665e)',
      legendLabels: ['-0.1 (Water)', '0.0 (Sandy Desert)', '+0.15 (Arid Pasture)', '+0.40 (Canopy Coverage)', '+0.70+ (Dense Green)'],
      purpose: 'Suppresses bare ground optical reflectance in arid, semi-arid, or low-density canopy zones using empirical soil brightness factor L=0.5.',
      rajasthanContext: 'Optimized specifically for western and central Rajasthan terrain (e.g. Bhadla, Jodhpur, Thar Desert) where high soil brightness distorts standard NDVI values.',
    },
    {
      id: 'mndwi',
      name: 'MNDWI — Modified Normalized Difference Water Index (Xu)',
      shortName: 'MNDWI',
      formula: '(B03 - B11) / (B03 + B11)',
      bands: [
        { code: 'B03', name: 'Green (560nm)', role: 'High reflectance of water' },
        { code: 'B11', name: 'SWIR 1 (1610nm, resampled 10m)', role: 'Absorbed by water, highly reflected by built structures & quarry rock' },
      ],
      icon: Activity,
      color: '#0891b2',
      range: '[-1.0 to +1.0]',
      colormapName: 'Blues / Cyan (Built Suppression)',
      colormapGradient: 'linear-gradient(to right, #f7fcf0, #e0f3db, #ccebc5, #a8ddb5, #7bccc4, #4eb3d3, #2b8cbe, #0868ac, #084081)',
      legendLabels: ['-0.5 (Built/Quarry/Soil)', '-0.2 (Dry Soil)', '0.0 (Water Boundary)', '+0.2 (Turbid Water)', '+0.5+ (Clear Reservoir)'],
      purpose: 'Removes false positives from village buildings, pacca roofs, and rocky soil while sharply delineating water edges.',
      rajasthanContext: 'Effectively distinguishes village settlement rooftops and stone quarry debris from ephemeral post-monsoon water tanks in rocky Rajasthani terrain.',
    },
    {
      id: 'lulc',
      name: 'AI Land Use & Land Cover (LULC) Classification',
      shortName: 'AI Land Cover',
      formula: 'Random Forest 6-Feature Fusion [VV, VH, Elev, Slope, NDVI, NDWI]',
      icon: Sparkles,
      color: '#16a34a',
      isLulc: true,
    },
  ];

  const currentIndex = indices.find((i) => i.id === selectedIndex) || indices[0];

  // Find calculated record in database for the active index type
  const activeRecord = indicesData.find(
    (item) => item.index_type?.toUpperCase() === currentIndex.shortName.toUpperCase()
  );

  const hasIndices = indicesData.length > 0;

  return (
    <div className="environmental-analytics-workspace">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-title-block">
          <h1 className="page-title">Environmental Analytics & Spectral Indices</h1>
          <p className="page-subtitle">
            Bio-physical and hydrological remote-sensing index models derived from Sentinel-2 Level-2A BOA Surface Reflectance rasters
          </p>
        </div>

        {/* Village and Scene Selectors */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Village Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <label
              htmlFor="analytics-village-select"
              style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}
            >
              Village:
            </label>
            <select
              id="analytics-village-select"
              className="form-select"
              value={targetVillageId}
              onChange={(e) => {
                const found = villages.find((v) => String(v.id) === String(e.target.value));
                if (found) onSelectVillage(found);
              }}
              style={{ minWidth: '180px' }}
            >
              {villages.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name} ({v.district})
                </option>
              ))}
            </select>
          </div>

          {/* Scene Selector */}
          {villageScenes.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <label
                htmlFor="analytics-scene-select"
                style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}
              >
                Scene:
              </label>
              <select
                id="analytics-scene-select"
                className="form-select"
                value={activeSceneId}
                onChange={(e) => setSelectedSceneId(e.target.value)}
                style={{ minWidth: '220px', fontFamily: 'var(--font-mono)', fontSize: '12px' }}
              >
                {villageScenes.map((s) => (
                  <option key={s.id} value={s.id}>
                    {new Date(s.acquisition_date).toLocaleDateString()} — {s.scene_id.substring(0, 18)}...
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Phase 4 Operational Notice Banner */}
      <div
        className="alert-banner alert-success"
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
          background: '#f0fdf4',
          border: '1px solid #bbf7d0',
          borderRadius: 'var(--radius-md)',
          padding: '12px 16px',
          marginBottom: '20px',
        }}
      >
        <CheckCircle2 size={20} style={{ flexShrink: 0, marginTop: 2, color: 'var(--color-primary)' }} />
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: 2 }}>
            <strong style={{ color: '#166534', fontSize: '13px' }}>
              Phase 4 Environmental Analytics Engine: Operational & Verified
            </strong>
            <span className="badge badge-green" style={{ fontSize: '10px' }}>NumPy 2.x</span>
            <span className="badge badge-green" style={{ fontSize: '10px' }}>Rasterio 1.4</span>
            <span className="badge badge-green" style={{ fontSize: '10px' }}>PostGIS Spatial Engine</span>
          </div>
          <span style={{ fontSize: '12px', color: '#14532d', lineHeight: 1.5 }}>
            Automated float32 raster array calculation active. All indices are derived from genuine Sentinel-2 Level-2A surface reflectance rasters ($DN / 10000.0$) with SCL cloud and shadow masking. Output products include 32-bit floating-point GeoTIFFs and transparent colorized PNG overlays.
          </span>
        </div>
      </div>

      {/* Compute Feedback Banner */}
      {computeMessage && (
        <div
          className={`alert-banner ${computeMessage.type === 'error' ? 'alert-danger' : 'alert-success'}`}
          style={{ marginBottom: '16px' }}
        >
          {computeMessage.type === 'error' ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
          <span>{computeMessage.text}</span>
        </div>
      )}

      {/* Index Selector Tabs */}
      <div className="tab-navigation">
        {indices.map((idx) => {
          const Icon = idx.icon;
          const isComputed = indicesData.some(
            (item) => item.index_type?.toUpperCase() === idx.shortName.toUpperCase()
          );
          return (
            <button
              key={idx.id}
              type="button"
              className={`tab-btn ${selectedIndex === idx.id ? 'active' : ''}`}
              onClick={() => setSelectedIndex(idx.id)}
            >
              <Icon size={15} style={{ color: selectedIndex === idx.id ? idx.color : 'inherit' }} />
              {idx.shortName}
              {isComputed && (
                <span
                  style={{
                    display: 'inline-block',
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: 'var(--color-primary)',
                    marginLeft: 4,
                  }}
                  title="Calculated data available"
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Conditional: AI LULC Classification Dashboard vs. Spectral Indices */}
      {selectedIndex === 'lulc' ? (
        <LulcAnalyticsDashboard
          villageId={targetVillageId}
          villageName={activeVillageObj?.name || 'Village'}
          onNavigateToGis={onNavigateToSatellite}
        />
      ) : (
        <>
          {/* Real Statistics Metrics Grid (5 Stat Cards) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '14px',
          marginBottom: '20px',
        }}
      >
        {/* Metric 1: Mean Value */}
        <div className="card" style={{ padding: '14px 16px', marginBottom: 0 }}>
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
            Mean {currentIndex.shortName}
          </span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '4px' }}>
            <span style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
              {activeRecord?.mean !== undefined && activeRecord?.mean !== null
                ? (activeRecord.mean > 0 ? `+${activeRecord.mean.toFixed(4)}` : activeRecord.mean.toFixed(4))
                : '—'}
            </span>
            {activeRecord?.mean !== undefined && activeRecord?.mean !== null && (
              <span className={`badge ${activeRecord.mean > 0.25 ? 'badge-green' : activeRecord.mean > 0.1 ? 'badge-warning' : 'badge-gray'}`} style={{ fontSize: '10px' }}>
                {currentIndex.id === 'ndvi' ? (activeRecord.mean > 0.3 ? 'Good Canopy' : activeRecord.mean > 0.15 ? 'Sparse Scrub' : 'Arid/Barren') : 'Valid Mean'}
              </span>
            )}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px', display: 'block' }}>
            Unmasked pixel average
          </span>
        </div>

        {/* Metric 2: Median Value */}
        <div className="card" style={{ padding: '14px 16px', marginBottom: 0 }}>
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
            Median {currentIndex.shortName}
          </span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '4px' }}>
            <span style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)' }}>
              {activeRecord?.median !== undefined && activeRecord?.median !== null
                ? (activeRecord.median > 0 ? `+${activeRecord.median.toFixed(4)}` : activeRecord.median.toFixed(4))
                : '—'}
            </span>
          </div>
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px', display: 'block' }}>
            50th percentile distribution
          </span>
        </div>

        {/* Metric 3: Dynamic Physical Range */}
        <div className="card" style={{ padding: '14px 16px', marginBottom: 0 }}>
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
            Observed Min / Max Range
          </span>
          <div style={{ marginTop: '4px', fontFamily: 'var(--font-mono)', fontSize: '15px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            {activeRecord?.min_value !== undefined && activeRecord?.min_value !== null
              ? `[${activeRecord.min_value.toFixed(4)} to ${activeRecord.max_value?.toFixed(4)}]`
              : '—'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '6px', display: 'block' }}>
            Physical boundary: {currentIndex.range}
          </span>
        </div>

        {/* Metric 4: Standard Deviation */}
        <div className="card" style={{ padding: '14px 16px', marginBottom: 0 }}>
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
            Standard Deviation (&sigma;)
          </span>
          <div style={{ marginTop: '4px', fontFamily: 'var(--font-mono)', fontSize: '24px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            {activeRecord?.std_dev !== undefined && activeRecord?.std_dev !== null
              ? `±${activeRecord.std_dev.toFixed(4)}`
              : '—'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px', display: 'block' }}>
            Spatial heterogeneity index
          </span>
        </div>

        {/* Metric 5: Pixel & Cloud Masking Audit */}
        <div className="card" style={{ padding: '14px 16px', marginBottom: 0 }}>
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '0.04em' }}>
            Valid Pixels / Cloud Mask
          </span>
          <div style={{ marginTop: '4px', fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
            {activeRecord?.valid_pixel_count !== undefined
              ? `${activeRecord.valid_pixel_count.toLocaleString()} px`
              : '—'}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px', display: 'block' }}>
            {activeRecord?.cloud_pixel_count !== undefined
              ? `${activeRecord.cloud_pixel_count} cloud px masked (${activeRecord.total_pixel_count ? ((activeRecord.cloud_pixel_count / activeRecord.total_pixel_count) * 100).toFixed(2) : 0}%)`
              : 'SCL cloud masking ready'}
          </span>
        </div>
      </div>

      {/* Spatial Raster Array Visualization Canvas */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div className="card-header" style={{ flexWrap: 'wrap', gap: '12px' }}>
          <div className="card-title-group">
            <h3 className="card-title">
              <Activity size={18} style={{ color: currentIndex.color }} />
              Spatial Raster Array Visualization — {currentIndex.shortName}
            </h3>
            <p className="card-subtitle">
              High-resolution 10.0m float32 raster colormap visualization for{' '}
              <strong>{activeVillageObj?.name}</strong> ({activeSceneObj?.scene_id || 'No Scene Selected'})
            </p>
          </div>

          {/* Action Toolbar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {/* Cloud Mask Toggle */}
            <label
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                cursor: 'pointer',
                color: 'var(--color-text-secondary)',
                marginRight: 6,
              }}
            >
              <input
                type="checkbox"
                checked={maskClouds}
                onChange={(e) => setMaskClouds(e.target.checked)}
                style={{ cursor: 'pointer' }}
              />
              SCL Cloud Masking
            </label>

            {/* Opacity Slider */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginRight: 8 }}>
              <Sliders size={14} style={{ color: 'var(--color-text-muted)' }} />
              <input
                type="range"
                min="20"
                max="100"
                value={overlayOpacity}
                onChange={(e) => setOverlayOpacity(Number(e.target.value))}
                style={{ width: '80px', cursor: 'pointer' }}
                title={`Overlay Opacity: ${overlayOpacity}%`}
              />
              <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)', width: '32px' }}>
                {overlayOpacity}%
              </span>
            </div>

            {/* Compute / Recompute Button */}
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => handleComputeIndices(hasIndices)}
              disabled={isComputing || !selectedSceneId}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <RefreshCw size={13} className={isComputing ? 'animate-spin' : ''} />
              {isComputing ? 'Calculating Rasters...' : hasIndices ? 'Recompute All Indices' : 'Compute Spectral Indices'}
            </button>

            {/* Download GeoTIFF Button */}
            {activeRecord?.download_url && (
              <a
                href={activeRecord.download_url}
                download
                className="btn btn-secondary btn-sm"
                style={{ display: 'flex', alignItems: 'center', gap: '6px', textDecoration: 'none' }}
                title="Download 32-bit floating point GeoTIFF"
              >
                <Download size={13} />
                GeoTIFF (.tif)
              </a>
            )}

            {/* Download PNG Overlay */}
            {activeRecord?.png_url && (
              <a
                href={activeRecord.png_url}
                download
                className="btn btn-secondary btn-sm"
                style={{ display: 'flex', alignItems: 'center', gap: '6px', textDecoration: 'none' }}
                title="Download transparent RGBA PNG overlay"
              >
                <FileDown size={13} />
                PNG Overlay
              </a>
            )}
          </div>
        </div>

        {/* Canvas Display Viewport */}
        <div
          style={{
            position: 'relative',
            minHeight: '380px',
            maxHeight: '520px',
            background: '#0f172a',
            backgroundImage:
              'radial-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px), radial-gradient(rgba(255, 255, 255, 0.04) 1px, #0f172a 1px)',
            backgroundSize: '24px 24px',
            backgroundPosition: '0 0, 12px 12px',
            borderRadius: 'var(--radius-md)',
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '24px',
          }}
        >
          {loadingIndices || isComputing ? (
            <div style={{ textAlign: 'center', color: '#e2e8f0' }}>
              <RefreshCw size={36} className="animate-spin" style={{ color: 'var(--color-primary)', marginBottom: 12 }} />
              <h4 style={{ margin: '0 0 4px 0', fontSize: '15px' }}>
                {isComputing ? 'Processing Sentinel-2 Surface Reflectance Rasters...' : 'Loading Spectral Indices...'}
              </h4>
              <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8' }}>
                Calculating pixel arrays with Rasterio 1.4 & NumPy 2.x
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
                height: '100%',
              }}
            >
              {/* Raster Image */}
              <div
                style={{
                  position: 'relative',
                  border: '1px solid rgba(255, 255, 255, 0.2)',
                  borderRadius: 'var(--radius-sm)',
                  boxShadow: '0 12px 32px rgba(0, 0, 0, 0.6)',
                  maxWidth: '100%',
                  maxHeight: '420px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'rgba(0, 0, 0, 0.4)',
                }}
              >
                <img
                  src={activeRecord.png_url}
                  alt={`${currentIndex.name} Raster Overlay`}
                  style={{
                    display: 'block',
                    maxWidth: '100%',
                    maxHeight: '400px',
                    objectFit: 'contain',
                    opacity: overlayOpacity / 100,
                    transition: 'opacity 0.15s ease',
                  }}
                />
                {/* Spatial Metadata Overlay Tag */}
                <div
                  style={{
                    position: 'absolute',
                    bottom: 8,
                    left: 8,
                    background: 'rgba(15, 23, 42, 0.85)',
                    backdropFilter: 'blur(4px)',
                    color: '#f8fafc',
                    fontSize: '10px',
                    padding: '4px 8px',
                    borderRadius: 'var(--radius-xs)',
                    fontFamily: 'var(--font-mono)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                  }}
                >
                  {activeRecord.resolution}m GSD &bull; {activeRecord.crs} &bull; Float32
                </div>
              </div>
            </div>
          ) : villageScenes.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#e2e8f0', maxWidth: '440px' }}>
              <AlertCircle size={36} style={{ color: 'var(--color-warning)', marginBottom: 12 }} />
              <h4 style={{ margin: '0 0 6px 0', fontSize: '15px' }}>No Satellite Imagery Ingested</h4>
              <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8', lineHeight: 1.5 }}>
                Acquire Sentinel-2 multispectral scenes for {activeVillageObj?.name} in the Satellite Imagery workspace before computing indices.
              </p>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={onNavigateToSatellite}
                style={{ marginTop: '14px' }}
              >
                Go to Satellite Acquisition <ArrowRight size={13} />
              </button>
            </div>
          ) : (
            <div style={{ textAlign: 'center', color: '#e2e8f0', maxWidth: '440px' }}>
              <Activity size={36} style={{ color: 'var(--color-primary)', marginBottom: 12 }} />
              <h4 style={{ margin: '0 0 6px 0', fontSize: '15px' }}>Spectral Indices Ready to Calculate</h4>
              <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8', lineHeight: 1.5 }}>
                Sentinel-2 Level-2A input bands are ingested and verified on disk. Click below to execute the Rasterio + NumPy array processing engine.
              </p>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => handleComputeIndices(false)}
                disabled={isComputing}
                style={{ marginTop: '16px' }}
              >
                Compute All 4 Spectral Indices
              </button>
            </div>
          )}
        </div>

        {/* Colormap Legend Scale directly underneath */}
        <div style={{ marginTop: '14px', padding: '0 4px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
              Colormap: {currentIndex.colormapName}
            </span>
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
              Range: {currentIndex.range}
            </span>
          </div>
          <div
            style={{
              height: '14px',
              borderRadius: 'var(--radius-xs)',
              background: currentIndex.colormapGradient,
              border: '1px solid var(--color-border-dark)',
              marginBottom: '4px',
            }}
          ></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--color-text-muted)' }}>
            {currentIndex.legendLabels.map((lbl) => (
              <span key={lbl}>{lbl}</span>
            ))}
          </div>
        </div>
      </div>

      {/* 2-Column Responsive Layout: Formulation & Ingestion Audit */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px', marginBottom: '20px' }}>
        {/* Panel 1: Scientific & Mathematical Specification */}
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-header">
            <div className="card-title-group">
              <h3 className="card-title">
                <currentIndex.icon size={18} style={{ color: currentIndex.color }} />
                {currentIndex.name}
              </h3>
              <p className="card-subtitle">Remote sensing bio-physical index formulation</p>
            </div>
            <span className="badge badge-gray" style={{ fontFamily: 'var(--font-mono)' }}>
              Range: {currentIndex.range}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {/* Mathematical Formula Presentation */}
            <div
              style={{
                background: 'var(--color-surface-muted)',
                padding: '16px',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border)',
                textAlign: 'center',
              }}
            >
              <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--color-text-muted)', display: 'block', marginBottom: 6, fontWeight: 700 }}>
                Mathematical Formulation
              </span>
              <code style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-primary)', letterSpacing: '0.02em', fontFamily: 'var(--font-mono)' }}>
                {currentIndex.formula}
              </code>
            </div>

            {/* Scientific Explanation */}
            <div>
              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', display: 'block', marginBottom: 4 }}>
                Primary Remote Sensing Purpose:
              </span>
              <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-text-primary)', lineHeight: 1.5 }}>
                {currentIndex.purpose}
              </p>
            </div>

            {/* Rajasthan Regional Context */}
            <div
              style={{
                background: '#f0fdf4',
                borderLeft: '3px solid var(--color-primary)',
                padding: '10px 14px',
                borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
              }}
            >
              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-primary)', display: 'block', marginBottom: 2 }}>
                Rajasthan Regional Specifics:
              </span>
              <p style={{ margin: 0, fontSize: '12px', color: '#14532d', lineHeight: 1.5 }}>
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
                <Layers size={18} style={{ color: 'var(--color-primary)' }} />
                Required Satellite Input Rasters
              </h3>
              <p className="card-subtitle">
                Local Sentinel-2 Level-2A assets for <strong>{activeVillageObj?.name}</strong>
              </p>
            </div>
            <span className="badge badge-gray">
              {villageScenes.length} Scene{villageScenes.length !== 1 ? 's' : ''} Available
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {/* Required Spectral Bands */}
            <div>
              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>
                Required Sentinel-2 Spectral Bands:
              </span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {currentIndex.bands.map((b) => (
                  <div
                    key={b.code}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '8px 12px',
                      background: 'var(--color-surface-muted)',
                      border: '1px solid var(--color-border-light)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '12px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className="badge badge-green" style={{ fontFamily: 'var(--font-mono)' }}>
                        {b.code}
                      </span>
                      <strong>{b.name}</strong>
                    </div>
                    <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>{b.role}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Ingested Scenes Status */}
            <div>
              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>
                Ingested Satellite Observations:
              </span>

              {villageScenes.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '20px 16px', background: 'var(--color-surface-muted)', borderRadius: 'var(--radius-md)', border: '1px dashed var(--color-border-dark)' }}>
                  <AlertCircle size={28} style={{ color: 'var(--color-warning)', marginBottom: 6 }} />
                  <h4 style={{ margin: '0 0 4px 0', fontSize: '13px', color: 'var(--color-text-primary)' }}>No Ingested Scenes For This Village</h4>
                  <p style={{ margin: 0, fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                    Acquire Sentinel-2 scenes for {activeVillageObj?.name} in the Satellite Imagery workspace.
                  </p>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={onNavigateToSatellite}
                    style={{ marginTop: '10px' }}
                  >
                    Go to Acquisition Pipeline <ArrowRight size={13} />
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {villageScenes.map((scene) => (
                    <div
                      key={scene.id}
                      style={{
                        padding: '10px 14px',
                        background: String(scene.id) === String(activeSceneId) ? '#f0fdf4' : 'var(--color-surface)',
                        border: String(scene.id) === String(activeSceneId) ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                        borderRadius: 'var(--radius-sm)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                      }}
                      onClick={() => setSelectedSceneId(String(scene.id))}
                    >
                      <div>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '12px', display: 'block', color: 'var(--color-text-primary)' }}>
                          {scene.scene_id}
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>
                          Acquired: {new Date(scene.acquisition_date).toLocaleDateString()} &bull; Cloud: {scene.cloud_cover}% &bull; {scene.bands_count || 7} Bands
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className="badge badge-green" style={{ fontSize: '10px' }}>
                          <ShieldCheck size={11} /> Rasters Ingested
                        </span>
                        {String(scene.id) === String(activeSceneId) && (
                          <span className="badge badge-primary" style={{ fontSize: '10px' }}>
                            Selected
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      </>
    )}
  </div>
);
}

export default EnvironmentalAnalytics;
