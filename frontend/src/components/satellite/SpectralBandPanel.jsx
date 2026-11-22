import React from 'react';
import { Download, Layers } from 'lucide-react';

const BAND_DESCRIPTIONS = {
  B02: { name: 'Blue', wavelength: '490 nm', use: 'Atmospheric scattering, bathymetry, water distinction' },
  B03: { name: 'Green', wavelength: '560 nm', use: 'Vegetation peak reflectance, water body mapping (NDWI)' },
  B04: { name: 'Red', wavelength: '665 nm', use: 'Chlorophyll absorption, vegetation health index (NDVI)' },
  B08: { name: 'Near Infrared (NIR)', wavelength: '842 nm', use: 'Vegetation canopy structure, moisture content' },
  B11: { name: 'SWIR 1', wavelength: '1610 nm', use: 'Soil moisture, snow/cloud discrimination, water index' },
  B12: { name: 'SWIR 2', wavelength: '2190 nm', use: 'Mineral and geology mapping, agricultural soil characterization' },
  SCL: { name: 'Scene Classification', wavelength: 'Discrete Mask', use: 'Cloud, cloud shadow, water, and vegetation classification' },
};

function SpectralBandPanel({ scene }) {
  if (!scene || !scene.bands || scene.bands.length === 0) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-text-secondary)', fontSize: '13px' }}>
        No individual band records found for this scene.
      </div>
    );
  }

  return (
    <div className="spectral-band-panel" style={{ marginTop: '16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
        <Layers size={16} style={{ color: 'var(--color-primary)' }} />
        <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 700, color: 'var(--color-text-primary)' }}>
          Multi-Spectral GeoTIFF Bands ({scene.bands.length} Bands Clipped to AOI)
        </h4>
      </div>

      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Band</th>
              <th>Spectral Designation</th>
              <th>Wavelength / Role</th>
              <th>Resolution</th>
              <th>Projected CRS</th>
              <th>Dimensions</th>
              <th>File Size</th>
              <th style={{ textAlign: 'right' }}>GeoTIFF Asset</th>
            </tr>
          </thead>
          <tbody>
            {scene.bands.map((band) => {
              const meta = BAND_DESCRIPTIONS[band.band_name] || { name: band.band_name, wavelength: 'N/A', use: 'Spectral data' };

              return (
                <tr key={band.id || band.band_name}>
                  <td>
                    <span className="badge badge-green" style={{ fontFamily: 'var(--font-mono)' }}>
                      {band.band_name}
                    </span>
                  </td>
                  <td>
                    <strong>{meta.name}</strong>
                  </td>
                  <td style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
                    <span>{meta.wavelength}</span> &bull; <span style={{ color: 'var(--color-text-muted)' }}>{meta.use}</span>
                  </td>
                  <td>{band.resolution}m</td>
                  <td>
                    <code style={{ fontSize: '11px', background: 'var(--color-surface-hover)', padding: '2px 5px', borderRadius: '4px' }}>
                      {band.crs?.split('[')?.[0] || 'EPSG:32643'}
                    </code>
                  </td>
                  <td style={{ fontSize: '12px' }}>
                    {band.width && band.height ? `${band.width} × ${band.height} px` : 'Clipped AOI'}
                  </td>
                  <td style={{ fontSize: '12px' }}>
                    {band.file_size_formatted || `${Math.round(band.file_size / 1024)} KB`}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <a
                      href={band.download_url}
                      target="_blank"
                      rel="noreferrer"
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: '11px', padding: '4px 10px', textDecoration: 'none' }}
                      title={`Download GeoTIFF for ${band.band_name}`}
                    >
                      <Download size={12} />
                      Download .TIF
                    </a>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default SpectralBandPanel;
