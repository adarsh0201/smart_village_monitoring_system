# Smart Village Monitoring System 🛰️🌾
> **AI-Powered Earth Observation & Geospatial Platform for Rural Development & Climate Resilience**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Django 5.2](https://img.shields.io/badge/Django-5.2-green.svg)](https://www.djangoproject.com/)
[![PostGIS 3.6](https://img.shields.io/badge/PostGIS-3.6-blue.svg)](https://postgis.net/)
[![Sentinel-1 SAR](https://img.shields.io/badge/Radar-Sentinel--1_SAR-orange.svg)](https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-1)
[![Sentinel-2 MSI](https://img.shields.io/badge/Optical-Sentinel--2_MSI-brightgreen.svg)](https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-2)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An enterprise-grade, end-to-end geospatial monitoring platform combining **Sentinel-2 Multi-Spectral Optical imagery**, **Sentinel-1 Dual-Pol Synthetic Aperture Radar (SAR)**, and official **Survey of India administrative village boundaries**. The platform provides automated biomass, water body, and infrastructure change detection across rural India, unaffected by cloud cover or seasonal weather barriers.

---

## 📑 Table of Contents
- [System Architecture](#-system-architecture)
- [Key Capabilities & Phases](#-key-capabilities--phases)
  - [Phase 1: Multi-State Geographic Foundation](#phase-1-multi-state-geographic-foundation)
  - [Phase 2: Sentinel-1 SAR Acquisition & Processing](#phase-2-sentinel-1-sar-acquisition--processing)
  - [Phase 3: Optical Multi-Spectral Analysis](#phase-3-optical-multi-spectral-analysis)
- [Pilot Villages Database](#-pilot-villages-database)
- [Installation & Setup](#-installation--setup)
- [Management Commands & CLI](#-management-commands--cli)
- [Mathematical & Radar Formulations](#-mathematical--radar-formulations)
- [Testing & Quality Assurance](#-testing--quality-assurance)

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Data_Sources ["🛰️ Earth Observation & Boundaries"]
        STAC_PC["Planetary Computer STAC API"]
        STAC_AWS["AWS Earth Search STAC"]
        SOI["Survey of India GeoJSON / Shapefiles"]
    end

    subgraph Backend ["⚙️ Django & PostGIS Core"]
        DB[("PostgreSQL 18 + PostGIS 3.6\n(MultiPolygons, Metric UTM 43N/44N)")]
        GEO_ENGINE["load_village_shapefile\n(Spatial Matching & Centroid Sync)"]
        SAR_ENGINE["sar_ingestion.py\n(Sub-pixel rasterio.mask + dB Calibration)"]
        OPT_ENGINE["optical_ingestion.py\n(SCL Cloud Masking + NDVI/NDWI/SAVI)"]
    end

    subgraph Storage ["💾 Analysis-Ready Storage"]
        TIFF["Clipped Cloud-Optimized GeoTIFFs\n(media/satellite/sar/village_<id>/)"]
        TILES["Transparent Colorized Overlays\n(media/satellite/indices/)"]
    end

    subgraph Frontend ["💻 Interactive Geospatial UI"]
        UI["React + Vite + Leaflet / MapLibre\n(Dynamic Layer Switching & Change Detection)"]
    end

    STAC_PC --> SAR_ENGINE
    STAC_AWS --> SAR_ENGINE
    SOI --> GEO_ENGINE
    GEO_ENGINE --> DB
    DB --> SAR_ENGINE
    DB --> OPT_ENGINE
    SAR_ENGINE --> TIFF
    OPT_ENGINE --> TILES
    DB --> UI
    TILES --> UI
```

---

## 🚀 Key Capabilities & Phases

### Phase 1: Multi-State Geographic Foundation
- **Official Cadastral Boundaries**: Direct ingestion of high-resolution Survey of India village boundaries (`MultiPolygonField`).
- **Dynamic Metric UTM Projections**: Eliminates latitude-dependent spherical distortions by automatically projecting to appropriate UTM zones:
  - **UTM Zone 43N (`EPSG:32643`)**: Western India / Rajasthan.
  - **UTM Zone 44N (`EPSG:32644`)**: Central & Northern India / Uttar Pradesh.
- **Centroid & Marker Pin Synchronization**: Guarantees zero offset (`0.00 km`) between database coordinates and boundary geometric centroids.
- **Bulk CSV Seeding Engine**: `seed_bulk_villages` command with header normalization, coordinate fallbacks, and automatic district centroid resolution.

### Phase 2: Sentinel-1 SAR Acquisition & Processing
Cloud-penetrating, day/night radar pipeline designed to maintain continuous monitoring during monsoon seasons and cloudy conditions:
- **STAC Asset Querying**: Searches `sentinel-1-rtc` (Radiometrically Terrain Corrected) and `sentinel-1-grd` IW (Interferometric Wide Swath) products.
- **Sub-Pixel Boundary Clipping**: Direct streaming and clipping using `rasterio.mask` against official PostGIS MultiPolygon geometries.
- **Radiometric Calibration**: Converts raw digital numbers (DN) to backscatter coefficient $\sigma^0$ in Decibels (dB).
- **Dual-Pol Cross-Ratio ($VH_{\text{dB}} - VV_{\text{dB}}$)**: Measures vegetation structure, canopy roughness, and biomass density.
- **Radar Vegetation Index (RVI)**: Dual-pol formulation estimating vegetation water content and cover.
- **Automated Database Indexing**: Registers bands and index products into `SatelliteScene`, `SatelliteBand`, and `SpectralIndex` with automated statistical summaries (mean, median, standard deviation, valid pixel count).

### Phase 3: Optical Multi-Spectral Analysis (Sentinel-2 Level-2A)
- **NDVI** (Normalized Difference Vegetation Index): Crop health and canopy greenness.
- **NDWI** (Normalized Difference Water Index - McFeeters): Surface water bodies and pond tracking.
- **SAVI** (Soil-Adjusted Vegetation Index): Vegetation in arid and semi-arid soils ($L=0.5$).
- **MNDWI** (Modified NDWI): Urban and turbid water discrimination.
- **SCL Cloud Masking**: Bitmask filtering using Sentinel-2 Scene Classification Layer.

---

## 📍 Pilot Villages Database

Currently verified and loaded in PostGIS with official Survey of India boundaries:

| State | District | Village Name | Boundary Geometry | UTM Zone |
| :--- | :--- | :--- | :---: | :---: |
| **Rajasthan** | Rajsamand | **Piplantri** | MultiPolygon | 43N (`EPSG:32643`) |
| **Rajasthan** | Rajsamand | **Kothariya** | MultiPolygon | 43N (`EPSG:32643`) |
| **Rajasthan** | Jhunjhunu | **Mandawa** | MultiPolygon | 43N (`EPSG:32643`) |
| **Rajasthan** | Phalodi | **Bhadla** | MultiPolygon | 43N (`EPSG:32643`) |
| **Rajasthan** | Jaisalmer | **Kuldhara** | MultiPolygon | 43N (`EPSG:32643`) |
| **Uttar Pradesh** | Ghazipur | **Gahmar** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Etawah | **Saifai** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Lucknow | **Juggaur** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Lucknow | **Itaunja** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Gorakhpur | **Dumri Khas** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Gorakhpur | **Bhatkaon** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Deoria | **Chainpur** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Deoria | **Sonbarsa** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Etawah | **Atirajpur** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Etawah | **Baidpura** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Etawah | **Parasana** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Etawah | **Phoolpur** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Etawah | **Tulsipur** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Etawah | **Ujhiyani** | MultiPolygon | 44N (`EPSG:32644`) |
| **Uttar Pradesh** | Barabanki | **Haswapara** | MultiPolygon | 44N (`EPSG:32644`) |

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- **Python**: 3.12+
- **Node.js**: 18+ and npm
- **Database**: PostgreSQL 16+ with **PostGIS 3.4+** extension enabled
- **GDAL**: Compatible GDAL runtime installed for Rasterio / GeoPandas

### 2. Backend Setup
```bash
# Clone the repository
git clone https://github.com/adarsh0201/smart_village_monitoring_system.git
cd smart_village_monitoring_system

# Create and activate virtual environment
python -m venv backend/venv
# Windows:
.\backend\venv\Scripts\activate
# Linux/macOS:
source backend/venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment variables
cp backend/.env.example backend/.env
# Edit backend/.env with your PostgreSQL credentials

# Run database migrations
python backend/manage.py migrate
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🛠️ Management Commands & CLI

### Seed Villages from CSV
```bash
# Dry run preview
python backend/manage.py seed_bulk_villages --file data/sample_villages.csv --dry-run

# Execute bulk creation/update
python backend/manage.py seed_bulk_villages --file data/sample_villages.csv
```

### Ingest Official Survey of India Boundaries
```bash
# Ingest Rajasthan boundaries
python backend/manage.py load_village_shapefile --geojson data/boundaries/rajasthan_pilot_villages.geojson --state "Rajasthan"

# Ingest Uttar Pradesh statewide boundaries
python backend/manage.py load_village_shapefile --geojson data/boundaries/vb_soi_up.GeoJSON --state "Uttar Pradesh"
```

### Search Sentinel-1 SAR Imagery
```bash
# Search available SAR passes over a village
python backend/manage.py search_sentinel1_sar --village Gahmar --limit 5
```

### Acquire & Process Sentinel-1 SAR Imagery
```bash
# Execute end-to-end streaming, clipping, dB calibration, and index calculation
python backend/manage.py acquire_sentinel1_sar --village Gahmar

# Force reprocessing of an existing scene
python backend/manage.py acquire_sentinel1_sar --village Saifai --force
```

---

## 📐 Mathematical & Radar Formulations

### 1. Radiometric SAR Calibration to Decibels (dB)
Converts linear backscatter intensity into logarithmic backscatter coefficient $\sigma^0$:
$$\sigma^0_{\text{dB}} = 10 \cdot \log_{10}\left(\max(\text{intensity}, 10^{-7})\right)$$

### 2. Dual-Pol Cross-Ratio (CR)
Measures depolarization caused by multi-bounce scattering inside crop canopies and structures:
$$\text{CR}_{\text{dB}} = VH_{\text{dB}} - VV_{\text{dB}}$$

### 3. Radar Vegetation Index (RVI)
Dual-polarization ratio estimating canopy development and biomass density:
$$\text{RVI} = \frac{4 \cdot VH_{\text{linear}}}{VV_{\text{linear}} + VH_{\text{linear}}}$$
* Range: $0$ (bare smooth soil, specular reflection) to $1$ (dense vegetated canopy, volume scattering).

### 4. Optical Spectral Indices (Sentinel-2)
- **NDVI**: $\frac{\text{B08} - \text{B04}}{\text{B08} + \text{B04}}$
- **NDWI**: $\frac{\text{B03} - \text{B08}}{\text{B03} + \text{B08}}$
- **SAVI**: $\frac{\text{B08} - \text{B04}}{\text{B08} + \text{B04} + 0.5} \times (1 + 0.5)$
- **MNDWI**: $\frac{\text{B03} - \text{B11}}{\text{B03} + \text{B11}}$

---

## 🧪 Testing & Quality Assurance

Run the automated test suite covering geospatial models, boundary logic, and satellite ingestion pipelines:

```bash
python backend/manage.py test villages satellite --noinput
```

All 29 tests verify model integrity, spatial centroid derivations, coordinate projections, and pipeline stability.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
