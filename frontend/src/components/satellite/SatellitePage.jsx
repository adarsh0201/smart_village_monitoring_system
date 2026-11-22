import React, { useState, useMemo } from 'react';
import { Search, HardDrive, RefreshCw } from 'lucide-react';
import SceneDiscovery from './SceneDiscovery';
import SatelliteLibrary from './SatelliteLibrary';

export function SatellitePage({
  villages = [],
  selectedVillage = null,
  onSelectVillage = () => {},
  scenes = [],
  onRefreshScenes = () => {},
}) {
  const [activeSubTab, setActiveSubTab] = useState('discovery'); // 'discovery' | 'library'

  const ingestedSceneIds = useMemo(() => {
    return new Set(scenes.map((s) => s.scene_id));
  }, [scenes]);

  const handleSceneIngested = () => {
    onRefreshScenes();
  };

  return (
    <div className="satellite-page-container">
      {/* Page Header */}
      <div className="page-header" style={{ marginBottom: 'var(--space-md)' }}>
        <div className="page-title-group">
          <h1 className="page-title">Satellite Imagery Pipeline</h1>
          <p className="page-subtitle">
            Sentinel-2 Level-2A Multi-Spectral Surface Reflectance Acquisition, Cloud Masking & GeoTIFF Ingestion
          </p>
        </div>

        {/* Sub-tab Navigation */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
          <div className="tab-navigation" style={{ marginBottom: 0 }}>
            <button
              type="button"
              className={`tab-btn ${activeSubTab === 'discovery' ? 'active' : ''}`}
              onClick={() => setActiveSubTab('discovery')}
            >
              <Search size={15} />
              STAC Scene Discovery
            </button>
            <button
              type="button"
              className={`tab-btn ${activeSubTab === 'library' ? 'active' : ''}`}
              onClick={() => setActiveSubTab('library')}
            >
              <HardDrive size={15} />
              Ingested Band Library
              <span className="badge badge-neutral" style={{ marginLeft: 6, fontSize: '0.7rem' }}>
                {scenes.length}
              </span>
            </button>
          </div>

          <button
            type="button"
            className="btn btn-outline btn-sm"
            onClick={onRefreshScenes}
            title="Refresh satellite scenes from PostGIS"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Active Tab View */}
      {activeSubTab === 'discovery' ? (
        <SceneDiscovery
          villages={villages}
          selectedVillage={selectedVillage}
          onSelectVillage={onSelectVillage}
          onSceneIngested={handleSceneIngested}
          ingestedSceneIds={ingestedSceneIds}
          onNavigateToLibrary={() => setActiveSubTab('library')}
        />
      ) : (
        <SatelliteLibrary
          villages={villages}
          selectedVillage={selectedVillage}
          onSelectVillage={onSelectVillage}
          scenes={scenes}
          onNavigateToDiscovery={() => setActiveSubTab('discovery')}
        />
      )}
    </div>
  );
}

export default SatellitePage;
