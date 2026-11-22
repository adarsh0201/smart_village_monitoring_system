import os
import re
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
import matplotlib
matplotlib.use('Agg')  # Headless rendering
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

from django.conf import settings
from satellite.models import SatelliteScene, SatelliteBand, SpectralIndex

RASTERIO_PROJ_DIR = os.path.join(os.path.dirname(rasterio.__file__), 'proj_data')


def format_crs_string(crs):
    """
    Format CRS into a clean string (e.g. 'EPSG:32643' or 'WGS 84 / UTM zone 43N').
    Falls back safely to truncated WKT or EPSG:4326.
    """
    if not crs:
        return "EPSG:4326"
    try:
        epsg = crs.to_epsg()
        if epsg:
            return f"EPSG:{epsg}"
    except Exception:
        pass

    crs_str = crs.to_string() if hasattr(crs, 'to_string') else str(crs)
    utm_match = re.search(r'UTM\s+zone\s+(\d+[NS]?)', crs_str, re.IGNORECASE)
    if utm_match:
        zone = utm_match.group(1).upper()
        # UTM 43N is EPSG 32643, UTM 42N is EPSG 32642
        zone_num = re.sub(r'[^0-9]', '', zone)
        if zone.endswith('N') and zone_num:
            return f"EPSG:326{int(zone_num):02d}"
        elif zone.endswith('S') and zone_num:
            return f"EPSG:327{int(zone_num):02d}"
        return f"WGS 84 / UTM zone {zone}"

    return crs_str[:450]


def sanitize_filename(name):
    """Sanitize scene identifier for safe cross-platform folder naming."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)


def load_and_scale_band(band_path, scale_factor=10000.0):
    """
    Load a Sentinel-2 GeoTIFF band and convert raw Digital Numbers (DN)
    into physical Top-Of-Canopy / Bottom-Of-Atmosphere surface reflectance.
    
    Level-2A data values are scaled by 10,000 (i.e. DN 10,000 = 1.0 reflectance).
    Zero and invalid values are converted to np.nan.
    
    Returns:
        tuple: (scaled_data: np.ndarray [float32], meta: dict)
    """
    if not os.path.isabs(band_path):
        band_path = os.path.join(settings.MEDIA_ROOT, band_path)

    if not os.path.exists(band_path):
        raise FileNotFoundError(f"Band raster file not found: {band_path}")

    with rasterio.open(band_path) as src:
        raw_data = src.read(1)
        meta = src.meta.copy()

    # Convert to float32 surface reflectance
    scaled = raw_data.astype(np.float32) / float(scale_factor)
    
    # 0 in Sentinel-2 Level-2A represents NoData (outside granule footprint)
    scaled[raw_data == 0] = np.nan
    if meta.get('nodata') is not None:
        scaled[raw_data == meta['nodata']] = np.nan

    return scaled, meta


def resample_to_reference(
    source_data,
    source_transform,
    source_crs,
    target_shape,
    target_transform,
    target_crs,
    resampling_method=Resampling.bilinear
):
    """
    Reproject and resample a 2D raster array to match a target reference grid.
    
    Uses Resampling.bilinear for continuous spectral data (e.g. B11 SWIR 20m -> 10m).
    Uses Resampling.nearest for discrete categorical masks (e.g. SCL 20m -> 10m).
    
    Returns:
        np.ndarray: Resampled array matching target_shape.
    """
    dst_dtype = source_data.dtype
    dst_data = np.empty(target_shape, dtype=dst_dtype)

    with rasterio.Env(PROJ_LIB=RASTERIO_PROJ_DIR, PROJ_DATA=RASTERIO_PROJ_DIR):
        reproject(
            source=source_data,
            destination=dst_data,
            src_transform=source_transform,
            src_crs=source_crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=resampling_method
        )
    return dst_data


def compute_scl_cloud_mask(
    scl_path,
    target_shape=None,
    target_transform=None,
    target_crs=None
):
    """
    Generate a boolean cloud & shadow mask from Sentinel-2 SCL (Scene Classification Layer).
    
    SCL Classes masked out:
      - 0: NO_DATA
      - 3: CLOUD_SHADOWS
      - 8: CLOUD_MEDIUM_PROBABILITY
      - 9: CLOUD_HIGH_PROBABILITY
      - 10: THIN_CIRRUS
      
    Returns:
        tuple: (mask: np.ndarray[bool] where True = masked out, cloud_pixel_count: int)
    """
    if not os.path.isabs(scl_path):
        scl_path = os.path.join(settings.MEDIA_ROOT, scl_path)

    if not os.path.exists(scl_path):
        raise FileNotFoundError(f"SCL raster file not found: {scl_path}")

    with rasterio.open(scl_path) as src:
        scl_data = src.read(1)
        scl_transform = src.transform
        scl_crs = src.crs

    # If target reference grid is specified and differs, resample SCL using NEAREST
    if target_shape is not None and target_shape != scl_data.shape:
        scl_aligned = resample_to_reference(
            source_data=scl_data.astype(np.uint8),
            source_transform=scl_transform,
            source_crs=scl_crs,
            target_shape=target_shape,
            target_transform=target_transform,
            target_crs=target_crs,
            resampling_method=Resampling.nearest
        )
    else:
        scl_aligned = scl_data

    # SCL mask classes: 0 (NoData), 3 (Cloud Shadow), 8 (Med Cloud), 9 (High Cloud), 10 (Cirrus)
    cloud_classes = [0, 3, 8, 9, 10]
    mask = np.isin(scl_aligned, cloud_classes)
    cloud_pixel_count = int(np.sum(mask))

    return mask, cloud_pixel_count


def calculate_ndvi(b08_nir, b04_red, mask=None):
    """
    Calculate Normalized Difference Vegetation Index (NDVI).
    Formula: (NIR - Red) / (NIR + Red) -> (B08 - B04) / (B08 + B04)
    """
    denom = b08_nir + b04_red
    valid_denom = np.abs(denom) > 1e-6

    ndvi = np.full(b08_nir.shape, np.nan, dtype=np.float32)
    np.divide(b08_nir - b04_red, denom, out=ndvi, where=valid_denom)

    # Clip to physical valid range [-1.0, 1.0]
    ndvi = np.clip(ndvi, -1.0, 1.0)

    if mask is not None:
        ndvi[mask] = np.nan

    return ndvi


def calculate_ndwi(b03_green, b08_nir, mask=None):
    """
    Calculate Normalized Difference Water Index (NDWI - McFeeters 1996).
    Formula: (Green - NIR) / (Green + NIR) -> (B03 - B08) / (B03 + B08)
    """
    denom = b03_green + b08_nir
    valid_denom = np.abs(denom) > 1e-6

    ndwi = np.full(b03_green.shape, np.nan, dtype=np.float32)
    np.divide(b03_green - b08_nir, denom, out=ndwi, where=valid_denom)

    ndwi = np.clip(ndwi, -1.0, 1.0)

    if mask is not None:
        ndwi[mask] = np.nan

    return ndwi


def calculate_savi(b08_nir, b04_red, L=0.5, mask=None):
    """
    Calculate Soil-Adjusted Vegetation Index (SAVI - Huete 1988).
    Formula: ((NIR - Red) / (NIR + Red + L)) * (1.0 + L)
    Requires surface reflectance scaled [0.0, 1.0] for L=0.5 to function correctly.
    """
    denom = b08_nir + b04_red + float(L)
    valid_denom = np.abs(denom) > 1e-6

    savi = np.full(b08_nir.shape, np.nan, dtype=np.float32)
    diff = b08_nir - b04_red
    np.divide(diff, denom, out=savi, where=valid_denom)
    savi = savi * (1.0 + float(L))

    savi = np.clip(savi, -1.0, 1.0)

    if mask is not None:
        savi[mask] = np.nan

    return savi


def calculate_mndwi(b03_green, b11_swir1, mask=None):
    """
    Calculate Modified Normalized Difference Water Index (MNDWI - Xu 2006).
    Formula: (Green - SWIR1) / (Green + SWIR1) -> (B03 - B11) / (B03 + B11)
    B11 (20m) must be resampled to 10m before passing to this function.
    """
    denom = b03_green + b11_swir1
    valid_denom = np.abs(denom) > 1e-6

    mndwi = np.full(b03_green.shape, np.nan, dtype=np.float32)
    np.divide(b03_green - b11_swir1, denom, out=mndwi, where=valid_denom)

    mndwi = np.clip(mndwi, -1.0, 1.0)

    if mask is not None:
        mndwi[mask] = np.nan

    return mndwi


def calculate_index_statistics(array, mask=None):
    """
    Calculate summary statistics over valid unmasked raster pixels.
    Ignores np.nan, np.inf, and -9999.0 nodata values.
    
    Returns:
        dict: {
            'valid_pixel_count': int,
            'total_pixel_count': int,
            'min_value': float or None,
            'max_value': float or None,
            'mean': float or None,
            'median': float or None,
            'std_dev': float or None
        }
    """
    total_pixels = int(array.size)

    # Valid mask
    valid_mask = np.isfinite(array) & (array != -9999.0)
    if mask is not None:
        valid_mask = valid_mask & (~mask)

    valid_vals = array[valid_mask]
    valid_count = int(valid_vals.size)

    if valid_count == 0:
        return {
            'valid_pixel_count': 0,
            'total_pixel_count': total_pixels,
            'min_value': None,
            'max_value': None,
            'mean': None,
            'median': None,
            'std_dev': None,
        }

    return {
        'valid_pixel_count': valid_count,
        'total_pixel_count': total_pixels,
        'min_value': round(float(np.min(valid_vals)), 4),
        'max_value': round(float(np.max(valid_vals)), 4),
        'mean': round(float(np.mean(valid_vals)), 4),
        'median': round(float(np.median(valid_vals)), 4),
        'std_dev': round(float(np.std(valid_vals)), 4),
    }


def export_index_geotiff(output_path, array, reference_meta, nodata=-9999.0):
    """
    Export calculated spectral index array as a standardized GeoTIFF.
    Uses Deflate compression and preserves spatial transform, CRS, and resolution.
    
    Args:
        output_path: Absolute or relative output file path
        array: 2D numpy array (float32)
        reference_meta: rasterio metadata dictionary from 10m reference band
        nodata: Value assigned to invalid or masked pixels (default -9999.0)
    """
    if not os.path.isabs(output_path):
        output_path = os.path.join(settings.MEDIA_ROOT, output_path)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    out_meta = reference_meta.copy()
    out_meta.update({
        'driver': 'GTiff',
        'height': array.shape[0],
        'width': array.shape[1],
        'count': 1,
        'dtype': 'float32',
        'nodata': float(nodata),
        'compress': 'deflate',
        'predictor': 3,
    })

    # Prepare array with nodata replacing nan
    out_arr = array.astype(np.float32).copy()
    out_arr[~np.isfinite(out_arr)] = float(nodata)

    with rasterio.Env(PROJ_LIB=RASTERIO_PROJ_DIR, PROJ_DATA=RASTERIO_PROJ_DIR):
        with rasterio.open(output_path, 'w', **out_meta) as dst:
            dst.write(out_arr, 1)

    return output_path


def render_colored_png_overlay(output_path, array, index_type, nodata=-9999.0):
    """
    Render a colorized RGBA PNG overlay for map visualization.
    Masked and nodata pixels are rendered fully transparent (alpha=0.0).
    Valid pixels are mapped to standard scientific colormaps with alpha=0.88.
    
    Colormap Schemes:
      - NDVI: RdYlGn (vmin=-0.1, vmax=0.8)
      - NDWI: Blues (vmin=-0.5, vmax=0.5)
      - SAVI: YlGn (vmin=-0.1, vmax=0.7)
      - MNDWI: Blues (vmin=-0.5, vmax=0.5)
    """
    if not os.path.isabs(output_path):
        output_path = os.path.join(settings.MEDIA_ROOT, output_path)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    valid_mask = np.isfinite(array) & (array != float(nodata))

    colormap_configs = {
        'NDVI': {'cmap': 'RdYlGn', 'vmin': -0.1, 'vmax': 0.8},
        'NDWI': {'cmap': 'Blues', 'vmin': -0.5, 'vmax': 0.5},
        'SAVI': {'cmap': 'YlGn', 'vmin': -0.1, 'vmax': 0.7},
        'MNDWI': {'cmap': 'Blues', 'vmin': -0.5, 'vmax': 0.5},
    }

    cfg = colormap_configs.get(index_type.upper(), {'cmap': 'viridis', 'vmin': -1.0, 'vmax': 1.0})
    cmap = plt.get_cmap(cfg['cmap'])
    norm = mcolors.Normalize(vmin=cfg['vmin'], vmax=cfg['vmax'], clip=True)

    # Convert array to RGBA
    colored = cmap(norm(array))

    # Mask transparency: Alpha channel = 0.0 for invalid, 0.88 for valid
    colored[~valid_mask, 3] = 0.0
    colored[valid_mask, 3] = 0.88

    plt.imsave(output_path, colored, format='png')
    return output_path


def compute_scene_indices(scene, mask_clouds=True, overwrite=False):
    """
    Orchestrate full computation of all four spectral indices (NDVI, NDWI, SAVI, MNDWI)
    for a completed Sentinel-2 SatelliteScene.
    
    Steps:
      1. Inspect and verify presence of required GeoTIFF bands (B03, B04, B08, B11, SCL).
      2. Load 10m reference bands (B04, B08, B03) and convert to surface reflectance.
      3. Resample 20m B11 to 10m reference grid using bilinear interpolation.
      4. If mask_clouds is True, resample SCL (20m -> 10m nearest) and generate cloud/shadow mask.
      5. Compute NDVI, NDWI, SAVI (L=0.5), and MNDWI rasters.
      6. Calculate rigorous descriptive statistics for each index.
      7. Export 32-bit floating point GeoTIFFs and RGBA PNG overlays.
      8. Persist SpectralIndex database records with statistics and file paths.
      
    Returns:
        dict: Summary of computed indices, statistics, and file paths.
    """
    safe_scene_id = sanitize_filename(scene.scene_id)
    village_id = str(scene.village_id)

    # Identify band records
    bands_by_name = {b.band_name: b for b in scene.bands.all()}
    required_keys = ['B04', 'B08', 'B03', 'B11']
    missing = [k for k in required_keys if k not in bands_by_name]
    if missing:
        raise ValueError(f"Scene {scene.scene_id} is missing required bands: {missing}")

    # Check existing indices if not overwrite
    if not overwrite:
        existing_completed = SpectralIndex.objects.filter(scene=scene, status='completed')
        if existing_completed.count() == 4:
            return {
                "success": True,
                "message": f"Indices already computed for scene {scene.scene_id}.",
                "cached": True,
                "indices": [
                    {
                        "index_type": idx.index_type,
                        "mean": idx.mean,
                        "median": idx.median,
                        "min_value": idx.min_value,
                        "max_value": idx.max_value,
                        "std_dev": idx.std_dev,
                        "valid_pixel_count": idx.valid_pixel_count,
                        "file_path": idx.file_path,
                        "png_path": idx.png_path,
                    }
                    for idx in existing_completed
                ]
            }

    # Output directory for indices
    rel_indices_dir = os.path.join("satellite", "indices", "villages", village_id, safe_scene_id)
    abs_indices_dir = os.path.join(settings.MEDIA_ROOT, rel_indices_dir)
    os.makedirs(abs_indices_dir, exist_ok=True)

    # 1. Load 10m reference bands
    b04_band = bands_by_name['B04']
    b04, ref_meta = load_and_scale_band(b04_band.file_path)
    ref_shape = (ref_meta['height'], ref_meta['width'])
    ref_transform = ref_meta['transform']
    ref_crs = ref_meta['crs']

    b08_band = bands_by_name['B08']
    b08, _ = load_and_scale_band(b08_band.file_path)

    b03_band = bands_by_name['B03']
    b03, _ = load_and_scale_band(b03_band.file_path)

    # 2. Load and resample 20m B11 band (bilinear)
    b11_band = bands_by_name['B11']
    b11_abs = os.path.join(settings.MEDIA_ROOT, b11_band.file_path)
    with rasterio.open(b11_abs) as b11_src:
        b11_raw = b11_src.read(1).astype(np.float32) / 10000.0
        b11_raw[b11_raw == 0] = np.nan
        b11_resampled = resample_to_reference(
            source_data=b11_raw,
            source_transform=b11_src.transform,
            source_crs=b11_src.crs,
            target_shape=ref_shape,
            target_transform=ref_transform,
            target_crs=ref_crs,
            resampling_method=Resampling.bilinear
        )

    # 3. Cloud Masking via SCL
    cloud_mask = None
    cloud_pixel_count = 0
    if mask_clouds and 'SCL' in bands_by_name:
        scl_band = bands_by_name['SCL']
        scl_abs = os.path.join(settings.MEDIA_ROOT, scl_band.file_path)
        cloud_mask, cloud_pixel_count = compute_scl_cloud_mask(
            scl_path=scl_abs,
            target_shape=ref_shape,
            target_transform=ref_transform,
            target_crs=ref_crs
        )

    # Combine cloud mask with NoData pixels in input bands
    nodata_mask = np.isnan(b04) | np.isnan(b08) | np.isnan(b03)
    if cloud_mask is not None:
        combined_mask = cloud_mask | nodata_mask
    else:
        combined_mask = nodata_mask

    # 4. Compute all 4 spectral indices
    index_computations = {
        'NDVI': {
            'array': calculate_ndvi(b08, b04, mask=combined_mask),
            'params': {},
            'description': 'Normalized Difference Vegetation Index',
        },
        'NDWI': {
            'array': calculate_ndwi(b03, b08, mask=combined_mask),
            'params': {},
            'description': 'Normalized Difference Water Index (McFeeters)',
        },
        'SAVI': {
            'array': calculate_savi(b08, b04, L=0.5, mask=combined_mask),
            'params': {'L': 0.5},
            'description': 'Soil-Adjusted Vegetation Index (Huete, L=0.5)',
        },
        'MNDWI': {
            'array': calculate_mndwi(b03, b11_resampled, mask=combined_mask),
            'params': {'resampling': 'bilinear_10m'},
            'description': 'Modified Normalized Difference Water Index (Xu)',
        },
    }

    results = []
    crs_str = format_crs_string(ref_crs)

    for idx_type, comp in index_computations.items():
        arr = comp['array']
        code_lower = idx_type.lower()

        # File paths
        tif_filename = f"{code_lower}.tif"
        png_filename = f"{code_lower}.png"
        rel_tif_path = os.path.join(rel_indices_dir, tif_filename).replace("\\", "/")
        rel_png_path = os.path.join(rel_indices_dir, png_filename).replace("\\", "/")
        abs_tif_path = os.path.join(abs_indices_dir, tif_filename)
        abs_png_path = os.path.join(abs_indices_dir, png_filename)

        # Export GeoTIFF and PNG
        export_index_geotiff(abs_tif_path, arr, ref_meta, nodata=-9999.0)
        render_colored_png_overlay(abs_png_path, arr, idx_type, nodata=-9999.0)

        # Calculate statistics
        stats = calculate_index_statistics(arr)

        # Database record
        index_obj, _ = SpectralIndex.objects.update_or_create(
            scene=scene,
            index_type=idx_type,
            defaults={
                'file_path': rel_tif_path,
                'png_path': rel_png_path,
                'resolution': 10.0,
                'crs': crs_str,
                'min_value': stats['min_value'],
                'max_value': stats['max_value'],
                'mean': stats['mean'],
                'median': stats['median'],
                'std_dev': stats['std_dev'],
                'valid_pixel_count': stats['valid_pixel_count'],
                'total_pixel_count': stats['total_pixel_count'],
                'cloud_masked': mask_clouds,
                'cloud_pixel_count': cloud_pixel_count,
                'status': 'completed',
                'error_message': None,
                'parameters': comp['params'],
            }
        )

        results.append({
            'id': index_obj.id,
            'index_type': idx_type,
            'mean': stats['mean'],
            'median': stats['median'],
            'min_value': stats['min_value'],
            'max_value': stats['max_value'],
            'std_dev': stats['std_dev'],
            'valid_pixel_count': stats['valid_pixel_count'],
            'total_pixel_count': stats['total_pixel_count'],
            'cloud_masked': mask_clouds,
            'cloud_pixel_count': cloud_pixel_count,
            'file_path': rel_tif_path,
            'png_path': rel_png_path,
        })

    return {
        "success": True,
        "scene_id": scene.scene_id,
        "village": scene.village.name,
        "indices_count": len(results),
        "indices": results,
    }
