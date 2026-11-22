import React, { useState } from 'react';
import { ArrowLeftRight, Clock, ArrowRight, GitCompare } from 'lucide-react';

export function ChangeDetection({
  villages = [],
  selectedVillage = null,
  onSelectVillage = () => {},
  scenes = [],
  onNavigateToSatellite = () => {},
}) {
  const targetVillageId = selectedVillage?.id ?? (villages[0]?.id ?? '');
  const activeVillageObj = villages.find((v) => String(v.id) === String(targetVillageId)) || villages[0];
  const villageScenes = scenes.filter((s) => String(s.village) === String(targetVillageId));

  const [t1SceneId, setT1SceneId] = useState(villageScenes[0]?.id || '');
  const [t2SceneId, setT2SceneId] = useState(villageScenes[1]?.id || villageScenes[0]?.id || '');

  const t1SceneObj = villageScenes.find((s) => String(s.id) === String(t1SceneId)) || villageScenes[0];
  const t2SceneObj = villageScenes.find((s) => String(s.id) === String(t2SceneId)) || villageScenes[1] || villageScenes[0];

  return (
    <div className="change-detection-workspace">
      {/* Page Header */}
      <div className="page-header">
        <div className="page-header-title-block">
          <h1 className="page-title">Multi-Temporal Change Detection</h1>
          <p className="page-subtitle">
            Bi-temporal spatial differencing (Δ = T₂ - T₁) for canopy shifts, water volume depletion & land degradation
          </p>
        </div>

        {/* Village Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <label htmlFor="change-village-select" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text-secondary)', textTransform: 'uppercase' }}>
            Village AOI:
          </label>
          <select
            id="change-village-select"
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

      {/* Notice Banner: Transparent Phase 5 Roadmap */}
      <div className="alert-banner alert-warning" style={{ alignItems: 'flex-start' }}>
        <Clock size={20} style={{ flexShrink: 0, marginTop: 2, color: 'var(--color-warning)' }} />
        <div>
          <strong style={{ display: 'block', marginBottom: 2 }}>
            Phase 5 Development Notice: Bi-Temporal Differential Engine Scheduled for Implementation
          </strong>
          <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
            Automated image coregistration, relative radiometric normalization, and pixel differencing will be activated in Phase 5.
            This workspace establishes the bi-temporal monitoring protocol and classification matrix for Rajasthan rural landscapes.
          </span>
        </div>
      </div>

      {/* Bi-Temporal Pair Configuration (Two Distinct Panels) */}
      <div className="card">
        <div className="card-header">
          <div className="card-title-group">
            <h3 className="card-title">
              <GitCompare size={17} style={{ color: 'var(--color-primary)' }} />
              Bi-Temporal Observation Granule Selection
            </h3>
            <p className="card-subtitle">
              Select baseline (T₁) and comparative (T₂) Sentinel-2 Level-2A surface reflectance granules for <strong>{activeVillageObj?.name}</strong>
            </p>
          </div>
          <span className="badge badge-blue">Differential Protocol</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '20px', alignItems: 'stretch' }}>
          {/* Panel 1: T1 Baseline Epoch */}
          <div
            style={{
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
              background: 'var(--color-surface-muted)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="badge badge-gray" style={{ fontWeight: 700 }}>
                Baseline Epoch (T₁)
              </span>
              <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Historical Reference State</span>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" htmlFor="t1-scene-select">Reference Sentinel-2 Scene</label>
              {villageScenes.length > 0 ? (
                <select
                  id="t1-scene-select"
                  className="form-select"
                  value={t1SceneId}
                  onChange={(e) => setT1SceneId(e.target.value)}
                >
                  {villageScenes.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.scene_id} ({new Date(s.acquisition_date).toLocaleDateString()})
                    </option>
                  ))}
                </select>
              ) : (
                <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', fontStyle: 'italic', padding: '8px 0' }}>
                  No scenes ingested for {activeVillageObj?.name}.
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 4 }}
                    onClick={onNavigateToSatellite}
                  >
                    Acquire Imagery <ArrowRight size={12} />
                  </button>
                </div>
              )}
            </div>

            {t1SceneObj && (
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', background: 'var(--color-surface)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-light)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span>Acquisition Date:</span>
                  <strong>{new Date(t1SceneObj.acquisition_date).toLocaleDateString()}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span>Cloud Cover:</span>
                  <strong>{t1SceneObj.cloud_cover}%</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Granule Provider:</span>
                  <span>{t1SceneObj.provider}</span>
                </div>
              </div>
            )}
          </div>

          {/* Comparison Operator */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 8px' }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: '50%',
                background: '#e8f5e9',
                color: 'var(--color-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <ArrowLeftRight size={20} />
            </div>
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--color-primary)', marginTop: 8, fontFamily: 'var(--font-mono)' }}>
              Δ = T₂ - T₁
            </span>
          </div>

          {/* Panel 2: T2 Comparative Epoch */}
          <div
            style={{
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
              background: 'var(--color-surface-muted)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="badge badge-blue" style={{ fontWeight: 700 }}>
                Comparative Epoch (T₂)
              </span>
              <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Target / Recent State</span>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" htmlFor="t2-scene-select">Target Sentinel-2 Scene</label>
              {villageScenes.length > 0 ? (
                <select
                  id="t2-scene-select"
                  className="form-select"
                  value={t2SceneId}
                  onChange={(e) => setT2SceneId(e.target.value)}
                >
                  {villageScenes.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.scene_id} ({new Date(s.acquisition_date).toLocaleDateString()})
                    </option>
                  ))}
                </select>
              ) : (
                <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', fontStyle: 'italic', padding: '8px 0' }}>
                  No scenes ingested for {activeVillageObj?.name}.
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 4 }}
                    onClick={onNavigateToSatellite}
                  >
                    Acquire Imagery <ArrowRight size={12} />
                  </button>
                </div>
              )}
            </div>

            {t2SceneObj && (
              <div style={{ fontSize: '12px', color: 'var(--color-text-secondary)', background: 'var(--color-surface)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border-light)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span>Acquisition Date:</span>
                  <strong>{new Date(t2SceneObj.acquisition_date).toLocaleDateString()}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span>Cloud Cover:</span>
                  <strong>{t2SceneObj.cloud_cover}%</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Granule Provider:</span>
                  <span>{t2SceneObj.provider}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Difference Calculation Specification */}
      <div className="card">
        <div className="card-header">
          <div className="card-title-group">
            <h3 className="card-title">
              Bi-Temporal Spatial Differencing Formulas
            </h3>
            <p className="card-subtitle">Pixel-by-pixel mathematical differential equations</p>
          </div>
          <span className="badge badge-warning">
            <Clock size={11} /> Phase 5 Standby
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '14px', marginBottom: '8px' }}>
          <div style={{ background: 'var(--color-surface-muted)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', display: 'block', marginBottom: 4 }}>
              Vegetation Difference (Δ NDVI):
            </span>
            <code style={{ fontSize: '14px', fontWeight: 700, color: 'var(--color-primary)', fontFamily: 'var(--font-mono)' }}>
              Δ NDVI = NDVI(T₂) - NDVI(T₁)
            </code>
            <p style={{ margin: '6px 0 0', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
              Tracks positive canopy growth (revegetation) vs negative canopy loss (drought/clearing).
            </p>
          </div>

          <div style={{ background: 'var(--color-surface-muted)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-secondary)', textTransform: 'uppercase', display: 'block', marginBottom: 4 }}>
              Water Body Difference (Δ NDWI):
            </span>
            <code style={{ fontSize: '14px', fontWeight: 700, color: '#0284c7', fontFamily: 'var(--font-mono)' }}>
              Δ NDWI = NDWI(T₂) - NDWI(T₁)
            </code>
            <p style={{ margin: '6px 0 0', fontSize: '12px', color: 'var(--color-text-secondary)' }}>
              Quantifies post-monsoon storage expansion vs summer evaporation of village johads.
            </p>
          </div>
        </div>
      </div>

      {/* Environmental Change Typology Table */}
      <div className="card">
        <div className="card-header">
          <div className="card-title-group">
            <h3 className="card-title">Rajasthan Environmental Change Typology</h3>
            <p className="card-subtitle">
              Automated classification thresholds for bi-temporal pixel categorization
            </p>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Transition Category</th>
                <th>Mathematical Threshold</th>
                <th>Ground Significance</th>
                <th>Administrative Protocol</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <span className="badge badge-green" style={{ fontWeight: 700 }}>
                    Vegetation Canopy Expansion
                  </span>
                </td>
                <td>
                  <code className="cell-code">Δ NDVI &gt; +0.15</code>
                </td>
                <td>Kharif crop maturation, social forestry survival, or post-monsoon greening.</td>
                <td>Afforestation survival audit; carbon sequestration recording.</td>
              </tr>
              <tr>
                <td>
                  <span className="badge badge-danger" style={{ fontWeight: 700 }}>
                    Vegetation Canopy Depletion
                  </span>
                </td>
                <td>
                  <code className="cell-code">Δ NDVI &lt; -0.15</code>
                </td>
                <td>Severe agricultural drought stress, deforestation, tree felling, or crop harvesting.</td>
                <td>Automated drought advisory alert; field verification dispatch.</td>
              </tr>
              <tr>
                <td>
                  <span className="badge badge-blue" style={{ fontWeight: 700 }}>
                    Surface Water Recharging
                  </span>
                </td>
                <td>
                  <code className="cell-code">Δ NDWI &gt; +0.20</code>
                </td>
                <td>Village johad/pond filling following seasonal rainfall; irrigation canal activation.</td>
                <td>Groundwater recharge estimation; reservoir volume assessment.</td>
              </tr>
              <tr>
                <td>
                  <span className="badge badge-amber" style={{ fontWeight: 700 }}>
                    Surface Water Desiccation
                  </span>
                </td>
                <td>
                  <code className="cell-code">Δ NDWI &lt; -0.20</code>
                </td>
                <td>Seasonal evaporation of ephemeral tanks; water table depression.</td>
                <td>Drought warning indicator for livestock water availability.</td>
              </tr>
              <tr>
                <td>
                  <span className="badge badge-gray" style={{ fontWeight: 700 }}>
                    Stable Land / Soil
                  </span>
                </td>
                <td>
                  <code className="cell-code">|Δ NDVI| &le; 0.15</code>
                </td>
                <td>Stable rocky terrain, arid scrubland, or constant built-up surface.</td>
                <td>Baseline environmental equilibrium verified.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default ChangeDetection;