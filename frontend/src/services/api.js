import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Fetch backend health & service status (GET /api/)
export const getApiStatus = async () => {
  const response = await api.get('');
  return response.data;
};

// Fetch list of villages (GET /api/villages/)
export const getVillages = async () => {
  const response = await api.get('villages/');
  return response.data;
};

// Search Sentinel-2 scenes for a village AOI (POST /api/satellite/search/)
export const searchSatelliteScenes = async (searchParams) => {
  const response = await api.post('satellite/search/', searchParams, { timeout: 30000 });
  return response.data;
};

// Download / window-clip Sentinel-2 bands for a village AOI (POST /api/satellite/download/)
export const downloadSatelliteScene = async (downloadParams) => {
  const response = await api.post('satellite/download/', downloadParams, { timeout: 120000 });
  return response.data;
};

// Fetch all ingested satellite scenes (GET /api/satellite/scenes/)
export const getSatelliteScenes = async (villageId = null) => {
  const url = villageId ? `satellite/scenes/?village_id=${villageId}` : 'satellite/scenes/';
  const response = await api.get(url);
  return response.data;
};

// Fetch satellite scenes for a specific village (GET /api/villages/<id>/satellite-scenes/)
export const getVillageSatelliteScenes = async (villageId) => {
  const response = await api.get(`villages/${villageId}/satellite-scenes/`);
  return response.data;
};

// Fetch computed spectral indices for a scene (GET /api/satellite/scenes/<id>/indices/)
export const getSceneIndices = async (sceneId) => {
  const response = await api.get(`satellite/scenes/${sceneId}/indices/`);
  return response.data;
};

// Trigger calculation of spectral indices for a scene (POST /api/satellite/scenes/<id>/compute-indices/)
export const computeSceneIndices = async (sceneId, options = {}) => {
  const response = await api.post(`satellite/scenes/${sceneId}/compute-indices/`, options, { timeout: 60000 });
  return response.data;
};

// Get Predicted LULC Transparent PNG map URL (GET /api/villages/<id>/predicted-map/)
export const getVillagePredictedMapUrl = (villageId, opacity = null) => {
  const base = `http://127.0.0.1:8000/api/villages/${villageId}/predicted-map/`;
  return opacity !== null ? `${base}?opacity=${opacity}` : base;
};

// Fetch LULC hectare analytics breakdown and Leaflet bounds (GET /api/villages/<id>/analytics/)
export const getVillageLulcAnalytics = async (villageId) => {
  const response = await api.get(`villages/${villageId}/analytics/`);
  return response.data;
};

export default api;
