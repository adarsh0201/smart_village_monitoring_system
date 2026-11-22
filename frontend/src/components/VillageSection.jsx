import React, { useState } from 'react';

function VillageSection({ villages, rawJson, selectedVillage = null, onSelectVillage = () => {} }) {
  const [showRawJson, setShowRawJson] = useState(false);

  return (
    <section className="village-section">
      <div className="section-header">
        <div>
          <h2 className="section-title">Village Monitoring Records</h2>
          <p className="section-subtitle">
            Ground units mapped and monitored via satellite data integration &bull; Click any row to focus on the GIS map
          </p>
        </div>
        <button
          type="button"
          className="btn-toggle-json"
          onClick={() => setShowRawJson(!showRawJson)}
        >
          {showRawJson ? 'Hide Raw JSON' : 'View Raw JSON from Django'}
        </button>
      </div>

      {showRawJson && (
        <div className="raw-json-panel">
          <div className="raw-json-header">
            <span>GET /api/villages/ — Direct Django REST Response</span>
          </div>
          <pre className="raw-json-code">
            {JSON.stringify(rawJson || villages, null, 2)}
          </pre>
        </div>
      )}

      {villages.length === 0 ? (
        <div className="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <p>No villages found in Django backend response.</p>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="village-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Village Name</th>
                <th>District</th>
                <th>State</th>
                <th>Coordinates (Lat, Lng)</th>
                <th>Area (Hectares)</th>
                <th>Boundary Status</th>
                <th>Monitoring</th>
              </tr>
            </thead>
            <tbody>
              {villages.map((village) => {
                const isSelected = selectedVillage?.id === village.id;
                const lat = village.latitude ?? village.location?.coordinates?.[1];
                const lng = village.longitude ?? village.location?.coordinates?.[0];

                return (
                  <tr
                    key={village.id || village.name}
                    className={isSelected ? 'selected-village-row' : ''}
                    onClick={() => onSelectVillage && onSelectVillage(village)}
                    style={{ cursor: 'pointer' }}
                    title="Click to locate on GIS map"
                  >
                    <td className="cell-id">#{village.id}</td>
                    <td className="cell-name">
                      <strong>{village.name}</strong>
                    </td>
                    <td>{village.district || 'Unassigned'}</td>
                    <td>
                      <span className="badge-state">{village.state || 'Rajasthan'}</span>
                    </td>
                    <td className="cell-coords">
                      {lat != null && lng != null
                        ? `${lat.toFixed(4)}°, ${lng.toFixed(4)}°`
                        : 'Pending'}
                    </td>
                    <td>
                      {village.area_hectares != null ? `${village.area_hectares} ha` : 'Pending GIS Calc'}
                    </td>
                    <td>
                      <span className={`badge-boundary ${village.boundary ? 'available' : 'point-only'}`}>
                        {village.boundary ? 'Polygon' : 'Point Only'}
                      </span>
                    </td>
                    <td>
                      <span className="badge-active">Active</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default VillageSection;
