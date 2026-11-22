import React from 'react';
import { MapPin, Satellite, CheckCircle } from 'lucide-react';

function VillageTable({
  villages = [],
  selectedVillage = null,
  onSelectVillage = () => {},
  onNavigateToGis = () => {},
  onNavigateToSatellite = () => {},
  sceneCountsByVillage = {},
}) {
  if (villages.length === 0) {
    return (
      <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
        No villages match the active search filter.
      </div>
    );
  }

  return (
    <div className="table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Village Name</th>
            <th>District</th>
            <th>State</th>
            <th>Coordinates (EPSG:4326)</th>
            <th>Area (Hectares)</th>
            <th>Boundary Type</th>
            <th>Satellite Scenes</th>
            <th>Monitoring</th>
            <th style={{ textAlign: 'right' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {villages.map((village) => {
            const isSelected = selectedVillage?.id === village.id;
            const lat = village.latitude ?? village.location?.coordinates?.[1];
            const lng = village.longitude ?? village.location?.coordinates?.[0];
            const scenesCount = sceneCountsByVillage[village.id] || 0;

            return (
              <tr
                key={village.id || village.name}
                className={isSelected ? 'row-selected' : ''}
              >
                <td style={{ fontWeight: 600, color: 'var(--color-text-secondary)', fontSize: '12px' }}>
                  #{village.id}
                </td>
                <td>
                  <strong style={{ color: 'var(--color-primary)', fontSize: '14px' }}>
                    {village.name}
                  </strong>
                </td>
                <td>{village.district || 'Unassigned'}</td>
                <td>
                  <span className="badge badge-gray">{village.state || 'Rajasthan'}</span>
                </td>
                <td style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                  {lat != null && lng != null ? `${lat.toFixed(4)}°, ${lng.toFixed(4)}°` : 'Pending'}
                </td>
                <td>
                  {village.area_hectares != null ? `${village.area_hectares} ha` : 'Pending GIS Calc'}
                </td>
                <td>
                  <span className={`badge ${village.boundary ? 'badge-green' : 'badge-amber'}`}>
                    {village.boundary ? 'Official Polygon' : 'Provisional Point'}
                  </span>
                </td>
                <td>
                  <span className={`badge ${scenesCount > 0 ? 'badge-green' : 'badge-gray'}`}>
                    {scenesCount > 0 ? `${scenesCount} Ingested` : '0 Scenes'}
                  </span>
                </td>
                <td>
                  <span className="badge badge-green">
                    <CheckCircle size={11} />
                    Active
                  </span>
                </td>
                <td style={{ textAlign: 'right' }}>
                  <div style={{ display: 'inline-flex', gap: '6px' }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      style={{ padding: '4px 8px', fontSize: '11px' }}
                      onClick={() => {
                        onSelectVillage(village);
                        onNavigateToGis();
                      }}
                      title="Locate and zoom on GIS map"
                    >
                      <MapPin size={12} />
                      GIS Map
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      style={{ padding: '4px 8px', fontSize: '11px' }}
                      onClick={() => {
                        onSelectVillage(village);
                        onNavigateToSatellite();
                      }}
                      title="Acquire Sentinel-2 imagery"
                    >
                      <Satellite size={12} />
                      Acquire
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default VillageTable;

