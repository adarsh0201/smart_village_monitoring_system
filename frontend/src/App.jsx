import React, { useState, useEffect, useCallback } from 'react';
import AppLayout from './components/layout/AppLayout';
import Overview from './components/dashboard/Overview';
import VillageMap from './components/gis/VillageMap';
import VillageRegistry from './components/villages/VillageRegistry';
import SatellitePage from './components/satellite/SatellitePage';
import EnvironmentalAnalytics from './components/analytics/EnvironmentalAnalytics';
import ChangeDetection from './components/change-detection/ChangeDetection';
import Reports from './components/reports/Reports';
import Loading from './components/common/Loading';
import ErrorState from './components/common/ErrorState';
import { getApiStatus, getVillages, getSatelliteScenes } from './services/api';

function App() {
  const [activePage, setActivePage] = useState('overview');
  const [villages, setVillages] = useState([]);
  const [selectedVillage, setSelectedVillage] = useState(null);
  const [scenes, setScenes] = useState([]);
  const [backendStatus, setBackendStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  // Initial data loading on mount
  useEffect(() => {
    let isMounted = true;

    async function fetchInitialData() {
      try {
        const [statusRes, villagesRes, scenesRes] = await Promise.all([
          getApiStatus().catch((err) => {
            console.warn('Status check warning:', err);
            return null;
          }),
          getVillages(),
          getSatelliteScenes().catch((err) => {
            console.warn('Satellite scenes warning:', err);
            return [];
          }),
        ]);

        if (isMounted) {
          const villageList = Array.isArray(villagesRes) ? villagesRes : [];
          const scenesList = Array.isArray(scenesRes) ? scenesRes : [];

          setVillages(villageList);
          setScenes(scenesList);
          setBackendStatus(statusRes);
          setIsConnected(true);
          setSelectedVillage((prev) => {
            if (prev && villageList.some((v) => v.id === prev.id)) {
              return villageList.find((v) => v.id === prev.id);
            }
            return villageList[0] || null;
          });
          setIsLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          console.error('Failed to load application data:', err);
          setIsConnected(false);

          let msg = 'Failed to connect to the Django REST API server.';
          if (err.code === 'ERR_NETWORK') {
            msg = 'Network Error: Django server is unreachable at http://127.0.0.1:8000. Please ensure the backend is running.';
          } else if (err.response) {
            msg = `Server Error (${err.response.status}): ${err.response.statusText || 'Unable to fetch data'}`;
          } else if (err.message) {
            msg = err.message;
          }
          setError(msg);
          setIsLoading(false);
        }
      }
    }

    fetchInitialData();

    return () => {
      isMounted = false;
    };
  }, []);

  // Refresh handler for user action
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    setError(null);

    try {
      const [statusRes, villagesRes, scenesRes] = await Promise.all([
        getApiStatus().catch(() => null),
        getVillages(),
        getSatelliteScenes().catch(() => []),
      ]);

      const villageList = Array.isArray(villagesRes) ? villagesRes : [];
      const scenesList = Array.isArray(scenesRes) ? scenesRes : [];

      setVillages(villageList);
      setScenes(scenesList);
      setBackendStatus(statusRes);
      setIsConnected(true);
    } catch (err) {
      console.error('Refresh error:', err);
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  // Refresh satellite scenes specifically (after an ingestion)
  const refreshScenes = useCallback(async () => {
    try {
      const refreshed = await getSatelliteScenes();
      setScenes(Array.isArray(refreshed) ? refreshed : []);
    } catch (err) {
      console.warn('Failed to refresh satellite scenes:', err);
    }
  }, []);

  // Cross-page navigation helper
  const navigateTo = (page, village = null) => {
    setActivePage(page);
    if (village) {
      setSelectedVillage(village);
    }
  };

  return (
    <AppLayout
      activePage={activePage}
      onNavigate={setActivePage}
      villages={villages}
      scenes={scenes}
      selectedVillage={selectedVillage}
      onSelectVillage={setSelectedVillage}
      isConnected={isConnected}
      onRefresh={handleRefresh}
      isLoading={isRefreshing}
    >
      {/* Global Error Banner */}
      {error && (
        <div style={{ marginBottom: 'var(--space-lg)' }}>
          <ErrorState
            title="Django Backend Connection Error"
            message={error}
            onRetry={handleRefresh}
          />
        </div>
      )}

      {/* Main Workspace Router */}
      {isLoading ? (
        <Loading message="Connecting to PostGIS database & Sentinel-2 repositories..." />
      ) : (
        <>
          {activePage === 'overview' && (
            <Overview
              villages={villages}
              scenes={scenes}
              backendStatus={backendStatus}
              isConnected={isConnected}
              onNavigate={navigateTo}
            />
          )}

          {activePage === 'gis' && (
            <VillageMap
              villages={villages}
              selectedVillage={selectedVillage}
              onSelectVillage={setSelectedVillage}
              scenes={scenes}
              onNavigateToSatellite={(village) => navigateTo('satellite', village)}
              onRefresh={handleRefresh}
            />
          )}

          {activePage === 'villages' && (
            <VillageRegistry
              villages={villages}
              selectedVillage={selectedVillage}
              onSelectVillage={setSelectedVillage}
              scenes={scenes}
              onNavigate={navigateTo}
            />
          )}

          {activePage === 'satellite' && (
            <SatellitePage
              villages={villages}
              selectedVillage={selectedVillage}
              onSelectVillage={setSelectedVillage}
              scenes={scenes}
              onRefreshScenes={refreshScenes}
            />
          )}

          {activePage === 'analytics' && (
            <EnvironmentalAnalytics
              villages={villages}
              selectedVillage={selectedVillage}
              onSelectVillage={setSelectedVillage}
              scenes={scenes}
              onNavigateToSatellite={() => navigateTo('satellite')}
            />
          )}

          {activePage === 'change' && (
            <ChangeDetection
              villages={villages}
              selectedVillage={selectedVillage}
              onSelectVillage={setSelectedVillage}
              scenes={scenes}
              onNavigateToSatellite={() => navigateTo('satellite')}
            />
          )}

          {activePage === 'reports' && (
            <Reports
              villages={villages}
              selectedVillage={selectedVillage}
              onSelectVillage={setSelectedVillage}
              scenes={scenes}
            />
          )}
        </>
      )}
    </AppLayout>
  );
}

export default App;