"""
Copernicus DEM (GLO-30) Ingestion & Topographic Feature Extraction Service.

Production-grade pipeline for 30m Digital Elevation Model (DEM) and Topographic Slope:
1. STAC Discovery: Queries Microsoft Planetary Computer STAC API for the `cop-dem-glo-30`
   (Copernicus DEM 30m Global) collection intersecting official village PostGIS boundaries.
2. SAS Token Signing: Authenticates against Microsoft Planetary Computer SAS token endpoint
   to allow direct streaming of Cloud-Optimized GeoTIFFs (COGs).
3. Precision Masking: Clips DEM COGs precisely to the village MultiPolygon using `rasterio.mask`.
4. Topographic Slope Derivation: Implements Horn's 3x3 finite-difference algorithm (Horn 1981)
   to compute terrain slope in degrees (0° - 90°) with edge padding to eliminate nodata artifacts.
5. Sentinel Grid Alignment: Resamples and reprojects both Elevation and Slope to match the exact
   coordinate reference system (UTM Zone), affine transform, resolution, and pixel dimensions
   of existing Sentinel-1 / Sentinel-2 rasters for direct multi-modal U-Net machine learning stacking.
6. Analysis-Ready Export: Outputs Deflate-compressed GeoTIFFs into the standard asset storage directory.
"""

import os
import re
import math
import logging
import requests
import numpy as np

# Ensure PyProj / GDAL / Rasterio use compatible PROJ data directory
try:
    import rasterio
    r_proj = os.path.join(os.path.dirname(rasterio.__file__), "proj_data")
    if os.path.isdir(r_proj):
        os.environ["PROJ_LIB"] = r_proj
        os.environ["PROJ_DATA"] = r_proj
        try:
            import pyproj.datadir
            pyproj.datadir.set_data_dir(r_proj)
        except Exception:
            pass
except Exception:
    pass

import rasterio
from rasterio.mask import mask
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.features import geometry_mask
from scipy.ndimage import correlate, distance_transform_edt
from pyproj import Transformer
import shapely.geometry
from shapely.ops import transform

from django.conf import settings
from django.utils import timezone
from villages.models import Village
from satellite.models import SatelliteScene, SatelliteBand
from satellite.services.aoi import generate_village_monitoring_aoi

logger = logging.getLogger("satellite.dem_ingestion")

PLANETARY_COMPUTER_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PLANETARY_COMPUTER_SAS_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/token/cop-dem-glo-30"


def sanitize_filename(name):
    """Sanitize village or scene identifier for safe cross-platform filesystem paths."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", str(name).strip())


def resolve_village_instance(village_ref):
    """
    Resolve a Village model instance from an instance, integer PK, or name string.
    """
    if isinstance(village_ref, Village):
        return village_ref
    if isinstance(village_ref, int) or (isinstance(village_ref, str) and str(village_ref).isdigit()):
        return Village.objects.get(pk=int(village_ref))
    if isinstance(village_ref, str):
        v = Village.objects.filter(name__iexact=village_ref.strip()).first()
        if v:
            return v
    raise ValueError(f"Could not resolve village from identifier: {village_ref}")


def get_planetary_computer_dem_token():
    """
    Fetch a temporary Shared Access Signature (SAS) token from Microsoft
    Planetary Computer for authenticated Copernicus DEM (cop-dem-glo-30) downloads.
    """
    try:
        response = requests.get(PLANETARY_COMPUTER_SAS_URL, timeout=10)
        if response.status_code == 200:
            return response.json().get("token")
    except Exception as exc:
        logger.warning(f"Could not retrieve Planetary Computer DEM SAS token: {exc}")
    return None


def sign_dem_url(url, sas_token=None):
    """
    Append SAS token to an Azure blob storage asset URL.
    """
    if not url:
        return None
    if not sas_token:
        sas_token = get_planetary_computer_dem_token()
    if not sas_token or "sig=" in url:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{sas_token}"


def search_copernicus_dem_tiles(village, buffer_km=2.5, sign_urls=True):
    """
    Query Microsoft Planetary Computer STAC for cop-dem-glo-30 tiles intersecting the village AOI.

    Args:
        village (Village|str|int): Target village model or identifier.
        buffer_km (float): Fallback buffer in kilometers if no official boundary exists.
        sign_urls (bool): Whether to append SAS authentication tokens to COG asset URLs.

    Returns:
        list[dict]: Discovered DEM tile items with metadata and asset download links.
    """
    village_instance = resolve_village_instance(village)
    aoi_data = generate_village_monitoring_aoi(village_instance, buffer_km=buffer_km)
    bbox = aoi_data["bbox"]
    has_official_boundary = not aoi_data.get("is_provisional", True)

    payload = {
        "collections": ["cop-dem-glo-30"],
        "bbox": bbox,
        "limit": 10
    }

    # If official boundary GeoJSON geometry is available, use exact intersects geometry
    if has_official_boundary and "geojson" in aoi_data:
        payload["intersects"] = aoi_data["geojson"]
        payload.pop("bbox", None)

    logger.info(
        f"Querying Copernicus DEM STAC for '{village_instance.name}': "
        f"boundary={'Official MultiPolygon' if has_official_boundary else 'Centroid Buffer'}"
    )

    headers = {"Content-Type": "application/json"}
    response = requests.post(PLANETARY_COMPUTER_STAC_URL, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()

    sas_token = get_planetary_computer_dem_token() if sign_urls else None
    features = data.get("features", [])
    results = []

    for item in features:
        item_id = item.get("id")
        assets = item.get("assets", {})
        data_asset = assets.get("data", {})
        raw_href = data_asset.get("href")

        signed_href = sign_dem_url(raw_href, sas_token) if (raw_href and sign_urls) else raw_href

        results.append({
            "tile_id": item_id,
            "collection": "cop-dem-glo-30",
            "bbox": item.get("bbox"),
            "data_url": signed_href,
            "raw_url": raw_href,
            "rendered_preview": assets.get("rendered_preview", {}).get("href"),
            "properties": item.get("properties", {}),
            "is_signed": bool(sas_token)
        })

    logger.info(f"Discovered {len(results)} Copernicus DEM tile(s) for '{village_instance.name}'.")
    return results


def calculate_topographic_slope(dem_array, res_x, res_y, nodata_val=-9999.0):
    """
    Calculate terrain slope in degrees (0.0° - 90.0°) using Horn's 3x3 finite-difference method.

    Horn (1981) formula:
      dz/dx = ((c + 2f + i) - (a + 2d + g)) / (8 * res_x)
      dz/dy = ((g + 2h + i) - (a + 2b + c)) / (8 * res_y)
      slope_radians = arctan(sqrt((dz/dx)^2 + (dz/dy)^2))
      slope_degrees = rad2deg(slope_radians)

    Edge Artifact Prevention:
      Uses Euclidean Distance Transform to pad the valid boundary elevation outward into the
      nodata background before convolution. This guarantees that boundary pixels compute true
      topographic gradients rather than artificial 89.9° cliffs against the nodata floor.

    Args:
        dem_array (np.ndarray): 2D floating-point elevation raster (in meters).
        res_x (float): Horizontal pixel resolution in meters.
        res_y (float): Vertical pixel resolution in meters.
        nodata_val (float): Nodata marker value.

    Returns:
        np.ndarray: 2D array of slope in degrees with nodata preserved.
    """
    valid_mask = (dem_array != nodata_val) & ~np.isnan(dem_array) & ~np.isinf(dem_array)
    if not np.any(valid_mask):
        return np.full_like(dem_array, nodata_val, dtype=np.float32)

    # 1. Pad valid elevation outward to avoid artificial boundary cliff artifacts
    if np.all(valid_mask):
        padded_dem = dem_array.astype(np.float32)
    else:
        indices = distance_transform_edt(~valid_mask, return_distances=False, return_indices=True)
        padded_dem = dem_array[tuple(indices)].astype(np.float32)

    # 2. Horn 3x3 convolution kernels (res_x and res_y in meters)
    # kx measures rate of change in east-west direction (right - left)
    kx = np.array([
        [-1.0, 0.0, 1.0],
        [-2.0, 0.0, 2.0],
        [-1.0, 0.0, 1.0]
    ], dtype=np.float32) / (8.0 * float(res_x))

    # ky measures rate of change in north-south direction (bottom - top in raster rows)
    ky = np.array([
        [-1.0, -2.0, -1.0],
        [ 0.0,  0.0,  0.0],
        [ 1.0,  2.0,  1.0]
    ], dtype=np.float32) / (8.0 * float(res_y))

    dz_dx = correlate(padded_dem, kx, mode="nearest")
    dz_dy = correlate(padded_dem, ky, mode="nearest")

    gradient_mag = np.sqrt(dz_dx**2 + dz_dy**2)
    slope_degrees = np.degrees(np.arctan(gradient_mag)).astype(np.float32)

    # 3. Clip range to valid physical angles [0.0, 90.0]
    slope_degrees = np.clip(slope_degrees, 0.0, 90.0)

    # 4. Restore nodata mask
    slope_degrees[~valid_mask] = nodata_val

    return slope_degrees


def find_sentinel_reference_raster(village):
    """
    Locate an existing Sentinel-1 (SAR) or Sentinel-2 (optical) GeoTIFF for this village
    to use as the exact spatial reference grid (CRS, transform, width, height) for U-Net alignment.

    Args:
        village (Village): Village model instance.

    Returns:
        tuple[str, str]|None: (reference_raster_path, sensor_type) or None if none exist on disk.
    """
    # 1. Check Sentinel-1 SAR products first (most recent)
    sar_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "sar", f"village_{village.id}")
    if os.path.isdir(sar_dir):
        for root, _, files in os.walk(sar_dir):
            for candidate in ["VV_db.tif", "VH_db.tif", "SAR_CrossRatio_VH_VV.tif", "SAR_RVI.tif"]:
                if candidate in files:
                    p = os.path.join(root, candidate)
                    if os.path.isfile(p):
                        return p, "Sentinel-1 SAR"

    # 2. Check Sentinel-2 Optical products
    opt_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "villages", str(village.id))
    if os.path.isdir(opt_dir):
        for root, _, files in os.walk(opt_dir):
            for candidate in ["B04.tif", "B08.tif", "B02.tif", "B03.tif"]:
                if candidate in files:
                    p = os.path.join(root, candidate)
                    if os.path.isfile(p):
                        return p, "Sentinel-2 MSI"

    # 3. Check database registered bands
    band = SatelliteBand.objects.filter(scene__village=village).first()
    if band and band.file_path:
        full_p = os.path.join(settings.MEDIA_ROOT, band.file_path)
        if os.path.isfile(full_p):
            return full_p, "Sentinel DB Band"

    return None, None


def calculate_raster_statistics(array, nodata_val=-9999.0):
    """
    Calculate summary statistics for continuous spatial arrays, ignoring nodata and NaNs.
    """
    valid = (array != nodata_val) & ~np.isnan(array) & ~np.isinf(array)
    valid_count = int(np.count_nonzero(valid))
    total_count = int(array.size)

    if valid_count == 0:
        return {
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "std_dev": None,
            "valid_count": 0,
            "total_count": total_count,
        }

    valid_vals = array[valid]
    return {
        "min": round(float(np.min(valid_vals)), 4),
        "max": round(float(np.max(valid_vals)), 4),
        "mean": round(float(np.mean(valid_vals)), 4),
        "median": round(float(np.median(valid_vals)), 4),
        "std_dev": round(float(np.std(valid_vals)), 4),
        "valid_count": valid_count,
        "total_count": total_count,
    }


def download_and_clip_dem(
    village,
    output_dir=None,
    buffer_km=2.5,
    sign_urls=True
):
    """
    Download and clip the 30m Copernicus DEM directly to the village MultiPolygon.
    Computes both 30m native Elevation and 30m Topographic Slope GeoTIFFs.

    Args:
        village (Village|str|int): Target village.
        output_dir (str, optional): Target storage directory.
        buffer_km (float): Buffer fallback if village lacks boundary.
        sign_urls (bool): Sign STAC URLs with SAS token.

    Returns:
        dict: Metadata dictionary including paths to native 30m elevation and slope GeoTIFFs.
    """
    village_instance = resolve_village_instance(village)
    if not output_dir:
        output_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "dem", f"village_{village_instance.id}")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Fetch STAC DEM tiles
    tiles = search_copernicus_dem_tiles(village_instance, buffer_km=buffer_km, sign_urls=sign_urls)
    if not tiles:
        raise ValueError(f"No Copernicus DEM (cop-dem-glo-30) tiles found intersecting '{village_instance.name}'.")

    # 2. Prepare village boundary geometry
    aoi_data = generate_village_monitoring_aoi(village_instance, buffer_km=buffer_km)
    shape_obj = shapely.geometry.shape(aoi_data["geojson"])

    primary_tile = tiles[0]
    source_url = primary_tile["data_url"]

    elevation_30m_path = os.path.join(output_dir, "elevation_30m.tif")
    slope_30m_path = os.path.join(output_dir, "slope_30m.tif")

    # 3. Stream and clip DEM using rasterio.mask
    with rasterio.open(source_url) as src:
        src_crs = src.crs

        # Transform boundary geometry to DEM CRS if needed (Copernicus DEM is EPSG:4326)
        if src_crs is not None and not src_crs.is_geographic:
            transformer = Transformer.from_crs("EPSG:4326", src_crs, always_xy=True)
            transformed_geom = transform(transformer.transform, shape_obj)
            shapes = [transformed_geom]
            out_crs = src_crs
        else:
            shapes = [shape_obj]
            out_crs = "EPSG:4326"

        out_image, out_transform = mask(
            src,
            shapes,
            crop=True,
            all_touched=True,
            filled=True,
            nodata=-9999.0
        )

        dem_data = out_image[0].astype(np.float32)
        meta = src.meta.copy()

        # Compute metric pixel resolution for slope calculation
        # If in degrees, convert to meters at the center latitude
        res_x_deg = abs(out_transform.a)
        res_y_deg = abs(out_transform.e)

        if out_crs == "EPSG:4326" or (hasattr(out_crs, "is_geographic") and out_crs.is_geographic):
            center_lat = (aoi_data["bbox"][1] + aoi_data["bbox"][3]) / 2.0
            lat_rad = math.radians(center_lat)
            meters_per_deg_lat = 111132.954 - 559.822 * math.cos(2 * lat_rad) + 1.175 * math.cos(4 * lat_rad)
            meters_per_deg_lon = 111412.84 * math.cos(lat_rad) - 93.5 * math.cos(3 * lat_rad)
            res_x_meters = res_x_deg * meters_per_deg_lon
            res_y_meters = res_y_deg * meters_per_deg_lat
        else:
            res_x_meters = float(src.res[0])
            res_y_meters = float(src.res[1])

        # 4. Compute Topographic Slope
        slope_data = calculate_topographic_slope(
            dem_data,
            res_x=res_x_meters,
            res_y=res_y_meters,
            nodata_val=-9999.0
        )

        # 5. Write 30m Elevation GeoTIFF
        meta.update({
            "driver": "GTiff",
            "height": dem_data.shape[0],
            "width": dem_data.shape[1],
            "transform": out_transform,
            "crs": out_crs,
            "nodata": -9999.0,
            "compress": "deflate",
            "dtype": "float32",
            "count": 1
        })

        with rasterio.open(elevation_30m_path, "w", **meta) as dst:
            dst.write(dem_data, 1)
            dst.update_tags(
                DATASET="Copernicus DEM GLO-30",
                VARIABLE="Elevation (Orthometric Height)",
                UNITS="meters",
                RESOLUTION="30m",
                VILLAGE=village_instance.name,
                TILE_ID=primary_tile["tile_id"]
            )

        # 6. Write 30m Slope GeoTIFF
        with rasterio.open(slope_30m_path, "w", **meta) as dst:
            dst.write(slope_data, 1)
            dst.update_tags(
                DATASET="Copernicus DEM GLO-30 Derived",
                VARIABLE="Topographic Slope (Horn 1981)",
                UNITS="degrees",
                RESOLUTION="30m",
                VILLAGE=village_instance.name,
                ALGORITHM="Horn 3x3 Finite Difference"
            )

    elev_stats = calculate_raster_statistics(dem_data, nodata_val=-9999.0)
    slope_stats = calculate_raster_statistics(slope_data, nodata_val=-9999.0)

    return {
        "elevation_30m_path": elevation_30m_path,
        "slope_30m_path": slope_30m_path,
        "width": dem_data.shape[1],
        "height": dem_data.shape[0],
        "crs": str(out_crs),
        "res_x_meters": res_x_meters,
        "res_y_meters": res_y_meters,
        "elevation_stats": elev_stats,
        "slope_stats": slope_stats,
        "tile_id": primary_tile["tile_id"]
    }


def align_dem_to_sentinel(
    village,
    elevation_source_path,
    slope_source_path,
    reference_raster_path,
    output_dir=None
):
    """
    Reproject and align the 30m DEM and Slope to match the exact UTM grid, transform,
    and dimensions of an existing Sentinel raster (e.g. 10m Sentinel-1 or Sentinel-2).

    This enables seamless stacking with Sentinel bands for U-Net machine learning:
      [B02, B03, B04, B08, B11, B12, VV, VH, Elevation, Slope] -> shape: (10, H, W)

    Args:
        village (Village): Target village instance.
        elevation_source_path (str): Path to input 30m elevation GeoTIFF.
        slope_source_path (str): Path to input 30m slope GeoTIFF.
        reference_raster_path (str): Path to reference Sentinel GeoTIFF.
        output_dir (str, optional): Target output directory.

    Returns:
        dict: Metadata with paths and statistics for aligned rasters.
    """
    if not output_dir:
        output_dir = os.path.dirname(elevation_source_path)

    aligned_elev_path = os.path.join(output_dir, "elevation_aligned.tif")
    aligned_slope_path = os.path.join(output_dir, "slope_aligned.tif")

    # 1. Read Reference Sentinel Grid
    with rasterio.open(reference_raster_path) as ref_src:
        ref_crs = ref_src.crs
        ref_transform = ref_src.transform
        ref_width = ref_src.width
        ref_height = ref_src.height
        ref_shape = (ref_height, ref_width)
        ref_meta = ref_src.meta.copy()

    # 2. Reproject Elevation to Reference Grid (Bilinear for continuous surface)
    aligned_elev = np.full(ref_shape, -9999.0, dtype=np.float32)
    with rasterio.open(elevation_source_path) as src_elev:
        reproject(
            source=rasterio.band(src_elev, 1),
            destination=aligned_elev,
            src_transform=src_elev.transform,
            src_crs=src_elev.crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            src_nodata=-9999.0,
            dst_nodata=-9999.0,
            resampling=Resampling.bilinear
        )

    # 3. Apply Village Boundary Mask on the Reference Grid
    aoi_data = generate_village_monitoring_aoi(village)
    shape_obj = shapely.geometry.shape(aoi_data["geojson"])

    transformer = Transformer.from_crs("EPSG:4326", ref_crs, always_xy=True)
    transformed_geom = transform(transformer.transform, shape_obj)

    # Create boolean boundary mask (True inside boundary)
    inside_mask = geometry_mask(
        [transformed_geom],
        out_shape=ref_shape,
        transform=ref_transform,
        invert=True,
        all_touched=True
    )
    aligned_elev[~inside_mask] = -9999.0

    # 4. Compute Topographic Slope directly on the high-resolution aligned UTM grid
    # Pixel resolution in UTM is planar metric (e.g. 10.0m x 10.0m)
    res_x = float(abs(ref_transform.a))
    res_y = float(abs(ref_transform.e))

    aligned_slope = calculate_topographic_slope(
        aligned_elev,
        res_x=res_x,
        res_y=res_y,
        nodata_val=-9999.0
    )

    # 5. Save Aligned Elevation GeoTIFF
    ref_meta.update({
        "driver": "GTiff",
        "dtype": "float32",
        "nodata": -9999.0,
        "compress": "deflate",
        "count": 1
    })

    with rasterio.open(aligned_elev_path, "w", **ref_meta) as dst:
        dst.write(aligned_elev, 1)
        dst.update_tags(
            VARIABLE="Aligned Elevation",
            UNITS="meters",
            GRID="Aligned to Sentinel Reference",
            REFERENCE_RASTER=os.path.basename(reference_raster_path),
            VILLAGE=village.name
        )

    # 6. Save Aligned Slope GeoTIFF
    with rasterio.open(aligned_slope_path, "w", **ref_meta) as dst:
        dst.write(aligned_slope, 1)
        dst.update_tags(
            VARIABLE="Aligned Topographic Slope",
            UNITS="degrees",
            GRID="Aligned to Sentinel Reference",
            REFERENCE_RASTER=os.path.basename(reference_raster_path),
            VILLAGE=village.name
        )

    elev_stats = calculate_raster_statistics(aligned_elev, nodata_val=-9999.0)
    slope_stats = calculate_raster_statistics(aligned_slope, nodata_val=-9999.0)

    return {
        "aligned_elevation_path": aligned_elev_path,
        "aligned_slope_path": aligned_slope_path,
        "width": ref_width,
        "height": ref_height,
        "crs": ref_crs.to_string(),
        "resolution": (res_x, res_y),
        "elevation_stats": elev_stats,
        "slope_stats": slope_stats
    }


def ingest_village_dem(village, reference_raster_path=None, force_refresh=False):
    """
    Complete end-to-end Copernicus DEM ingestion & topographic feature extraction pipeline.

    1. STAC Discovery: Finds Copernicus DEM 30m GLO-30 tile for the village.
    2. Boundary Masking: Clips the DEM to the official PostGIS village boundary (`rasterio.mask`).
    3. Slope Calculation: Derives topographic slope in degrees using Horn's algorithm.
    4. Sentinel Grid Alignment: Reprojects and resamples both Elevation and Slope to match
       the exact coordinate grid (UTM Zone), affine transform, and pixel shape of existing Sentinel data.
    5. Storage: Saves GeoTIFFs to `media/satellite/dem/village_<id>/`.

    Args:
        village (Village|str|int): Target village model or identifier.
        reference_raster_path (str, optional): Explicit path to reference Sentinel raster for alignment.
        force_refresh (bool): Re-download and re-compute even if files exist.

    Returns:
        dict: Complete ingestion result manifest with file paths, stats, and metadata.
    """
    village_instance = resolve_village_instance(village)
    output_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "dem", f"village_{village_instance.id}")
    os.makedirs(output_dir, exist_ok=True)

    elevation_30m_file = os.path.join(output_dir, "elevation_30m.tif")
    slope_30m_file = os.path.join(output_dir, "slope_30m.tif")

    # 1. Check Cache / Idempotency for 30m products
    if not force_refresh and os.path.isfile(elevation_30m_file) and os.path.isfile(slope_30m_file):
        logger.info(f"Using cached 30m DEM and slope for '{village_instance.name}'.")
        with rasterio.open(elevation_30m_file) as src_e, rasterio.open(slope_30m_file) as src_s:
            dem_30m_res = {
                "elevation_30m_path": elevation_30m_file,
                "slope_30m_path": slope_30m_file,
                "width": src_e.width,
                "height": src_e.height,
                "crs": src_e.crs.to_string(),
                "elevation_stats": calculate_raster_statistics(src_e.read(1)),
                "slope_stats": calculate_raster_statistics(src_s.read(1)),
                "tile_id": src_e.tags().get("TILE_ID", "cached")
            }
    else:
        # Download and clip 30m Copernicus DEM
        dem_30m_res = download_and_clip_dem(village_instance, output_dir=output_dir)

    # 2. Determine Sentinel Reference Raster for Spatial Alignment
    sensor_type = "None"
    if not reference_raster_path:
        reference_raster_path, sensor_type = find_sentinel_reference_raster(village_instance)

    aligned_res = None
    if reference_raster_path and os.path.isfile(reference_raster_path):
        logger.info(f"Aligning DEM & Slope to reference Sentinel raster: {reference_raster_path} ({sensor_type})")
        aligned_res = align_dem_to_sentinel(
            village=village_instance,
            elevation_source_path=dem_30m_res["elevation_30m_path"],
            slope_source_path=dem_30m_res["slope_30m_path"],
            reference_raster_path=reference_raster_path,
            output_dir=output_dir
        )

    # 3. Build Return Manifest
    manifest = {
        "success": True,
        "village_id": village_instance.id,
        "village_name": village_instance.name,
        "district": village_instance.district,
        "state": village_instance.state,
        "dem_collection": "cop-dem-glo-30",
        "tile_id": dem_30m_res.get("tile_id"),
        "products": {
            "elevation_30m": dem_30m_res["elevation_30m_path"],
            "slope_30m": dem_30m_res["slope_30m_path"],
            "elevation_aligned": aligned_res["aligned_elevation_path"] if aligned_res else None,
            "slope_aligned": aligned_res["aligned_slope_path"] if aligned_res else None,
        },
        "aligned_to_sentinel": bool(aligned_res),
        "reference_raster": reference_raster_path,
        "reference_sensor": sensor_type,
        "statistics": {
            "elevation_30m": dem_30m_res["elevation_stats"],
            "slope_30m": dem_30m_res["slope_stats"],
            "elevation_aligned": aligned_res["elevation_stats"] if aligned_res else None,
            "slope_aligned": aligned_res["slope_stats"] if aligned_res else None,
        }
    }

    logger.info(f"Copernicus DEM & Slope processing complete for '{village_instance.name}'.")
    return manifest
