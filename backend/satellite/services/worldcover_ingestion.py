"""
ESA WorldCover (10m) Ingestion & Ground Truth Label Extraction Service.

Production-grade pipeline for Step 2: Ground Truth Labels for U-Net ML Training:
1. STAC Discovery: Queries Microsoft Planetary Computer STAC API for the `esa-worldcover`
   collection (10m Land Use / Land Cover) intersecting official village PostGIS boundaries.
2. SAS Token Signing: Authenticates against the Planetary Computer SAS token endpoint
   to allow direct streaming of Cloud-Optimized GeoTIFFs (COGs).
3. Precision Spatial Masking: Masks and clips the label raster to the exact village MultiPolygon boundary.
4. Nearest-Neighbor Alignment: Reprojects and aligns the discrete class raster to the exact UTM
   coordinate grid, 10.0m resolution, affine transform, and matrix dimensions of existing
   Sentinel / DEM rasters using `Resampling.nearest` to strictly preserve categorical class IDs.
5. Export: Saves `worldcover_aligned.tif` (uint8, nodata=0) ready to serve as the $y$ target mask
   for U-Net semantic segmentation training.
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
from pyproj import Transformer
import shapely.geometry
from shapely.ops import transform

from django.conf import settings
from django.utils import timezone
from villages.models import Village
from satellite.models import SatelliteScene, SatelliteBand
from satellite.services.aoi import generate_village_monitoring_aoi

logger = logging.getLogger("satellite.worldcover_ingestion")

PLANETARY_COMPUTER_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PLANETARY_COMPUTER_SAS_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/token/esa-worldcover"

# Official ESA WorldCover 11-Class Legend
ESA_WORLDCOVER_CLASSES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse vegetation",
    70: "Snow and ice",
    80: "Permanent water bodies",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}

# Hex colors for visualization and PNG generation
ESA_WORLDCOVER_COLORS = {
    10: "#006400",  # Dark Green (Tree cover)
    20: "#ffbb22",  # Orange-Yellow (Shrubland)
    30: "#ffff4c",  # Light Yellow (Grassland)
    40: "#f096ff",  # Pink/Violet (Cropland)
    50: "#fa0000",  # Red (Built-up)
    60: "#b4b4b4",  # Gray (Bare / sparse vegetation)
    70: "#f0f0f0",  # White (Snow/Ice)
    80: "#0064c8",  # Blue (Permanent water bodies)
    90: "#0096a0",  # Teal (Herbaceous wetland)
    95: "#00cf75",  # Green-Cyan (Mangroves)
    100: "#fae6a0", # Light Brown (Moss/Lichen)
}


def sanitize_filename(name):
    """Sanitize identifier for safe filesystem paths."""
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


def get_planetary_computer_worldcover_token():
    """
    Fetch a temporary Shared Access Signature (SAS) token from Microsoft
    Planetary Computer for authenticated ESA WorldCover blob asset downloads.
    """
    try:
        response = requests.get(PLANETARY_COMPUTER_SAS_URL, timeout=10)
        if response.status_code == 200:
            return response.json().get("token")
    except Exception as exc:
        logger.warning(f"Could not retrieve Planetary Computer WorldCover SAS token: {exc}")
    return None


def sign_worldcover_url(url, sas_token=None):
    """
    Append SAS token to an Azure blob storage asset URL.
    """
    if not url:
        return None
    if not sas_token:
        sas_token = get_planetary_computer_worldcover_token()
    if not sas_token or "sig=" in url:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{sas_token}"


def search_esa_worldcover_tiles(village, year=2021, buffer_km=2.5, sign_urls=True):
    """
    Query Microsoft Planetary Computer STAC for esa-worldcover tiles intersecting the village AOI.

    Args:
        village (Village|str|int): Target village model or identifier.
        year (int): WorldCover product year (2021 [v200] or 2020 [v100], default: 2021).
        buffer_km (float): Fallback buffer in kilometers if no official boundary exists.
        sign_urls (bool): Whether to sign Azure asset URLs with SAS tokens.

    Returns:
        list[dict]: Discovered WorldCover tile items with metadata and asset download links.
    """
    village_instance = resolve_village_instance(village)
    aoi_data = generate_village_monitoring_aoi(village_instance, buffer_km=buffer_km)
    bbox = aoi_data["bbox"]
    has_official_boundary = not aoi_data.get("is_provisional", True)

    payload = {
        "collections": ["esa-worldcover"],
        "bbox": bbox,
        "limit": 10
    }

    # If official boundary GeoJSON geometry is available, use exact intersects geometry
    if has_official_boundary and "geojson" in aoi_data:
        payload["intersects"] = aoi_data["geojson"]
        payload.pop("bbox", None)

    logger.info(
        f"Querying ESA WorldCover STAC for '{village_instance.name}': "
        f"year={year}, boundary={'Official MultiPolygon' if has_official_boundary else 'Centroid Buffer'}"
    )

    headers = {"Content-Type": "application/json"}
    response = requests.post(PLANETARY_COMPUTER_STAC_URL, json=payload, headers=headers, timeout=15)
    response.raise_for_status()
    data = response.json()

    sas_token = get_planetary_computer_worldcover_token() if sign_urls else None
    features = data.get("features", [])
    results = []

    # Filter features by requested year if available, otherwise pick the newest
    year_str = str(year)
    matching_features = [
        f for f in features
        if year_str in f.get("id", "") or year_str in str(f.get("properties", {}).get("datetime", ""))
    ]
    candidate_features = matching_features if matching_features else features

    for item in candidate_features:
        item_id = item.get("id")
        assets = item.get("assets", {})
        map_asset = assets.get("map", {})
        raw_href = map_asset.get("href")

        signed_href = sign_worldcover_url(raw_href, sas_token) if (raw_href and sign_urls) else raw_href

        results.append({
            "tile_id": item_id,
            "collection": "esa-worldcover",
            "bbox": item.get("bbox"),
            "data_url": signed_href,
            "raw_url": raw_href,
            "rendered_preview": assets.get("rendered_preview", {}).get("href"),
            "properties": item.get("properties", {}),
            "is_signed": bool(sas_token)
        })

    logger.info(f"Discovered {len(results)} ESA WorldCover tile(s) for '{village_instance.name}'.")
    return results


def find_reference_sentinel_raster(village):
    """
    Locate an existing Sentinel-1 (SAR), Sentinel-2 (optical), or DEM raster for this village
    to extract the exact spatial reference grid (CRS, transform, width, height) for U-Net alignment.

    Args:
        village (Village): Village model instance.

    Returns:
        tuple[str, str]|None: (reference_raster_path, sensor_type) or None if none exist on disk.
    """
    # 1. Check Sentinel-1 SAR products first
    sar_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "sar", f"village_{village.id}")
    if os.path.isdir(sar_dir):
        for root, _, files in os.walk(sar_dir):
            for candidate in ["VV_db.tif", "VH_db.tif", "SAR_CrossRatio_VH_VV.tif", "SAR_RVI.tif"]:
                if candidate in files:
                    p = os.path.join(root, candidate)
                    if os.path.isfile(p):
                        return p, "Sentinel-1 SAR"

    # 2. Check Aligned DEM
    dem_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "dem", f"village_{village.id}")
    if os.path.isdir(dem_dir):
        for candidate in ["elevation_aligned.tif", "slope_aligned.tif"]:
            p = os.path.join(dem_dir, candidate)
            if os.path.isfile(p):
                return p, "Aligned DEM"

    # 3. Check Sentinel-2 Optical products
    opt_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "villages", str(village.id))
    if os.path.isdir(opt_dir):
        for root, _, files in os.walk(opt_dir):
            for candidate in ["B04.tif", "B08.tif", "B02.tif", "B03.tif"]:
                if candidate in files:
                    p = os.path.join(root, candidate)
                    if os.path.isfile(p):
                        return p, "Sentinel-2 MSI"

    # 4. Check database registered bands
    band = SatelliteBand.objects.filter(scene__village=village).first()
    if band and band.file_path:
        full_p = os.path.join(settings.MEDIA_ROOT, band.file_path)
        if os.path.isfile(full_p):
            return full_p, "Sentinel DB Band"

    return None, None


def calculate_class_distribution(label_array, pixel_size_meters=10.0, nodata_val=0):
    """
    Calculate the area and percentage distribution of land cover classes in the raster mask.

    Args:
        label_array (np.ndarray): 2D integer class array.
        pixel_size_meters (float): Ground sampling distance in meters (default: 10.0).
        nodata_val (int): Nodata label value (default: 0).

    Returns:
        dict: Detailed breakdown of class pixel counts, percentages, and area in hectares.
    """
    valid_mask = (label_array != nodata_val)
    valid_count = int(np.count_nonzero(valid_mask))
    total_count = int(label_array.size)

    if valid_count == 0:
        return {
            "total_pixels": total_count,
            "valid_pixels": 0,
            "classes": {}
        }

    pixel_area_ha = (float(pixel_size_meters) ** 2) / 10000.0  # 10m * 10m = 100m² = 0.01 ha
    unique_classes, counts = np.unique(label_array[valid_mask], return_counts=True)

    class_breakdown = {}
    for cls_id, cnt in zip(unique_classes, counts):
        cls_id = int(cls_id)
        cnt = int(cnt)
        pct = round(float(cnt / valid_count * 100.0), 2)
        ha = round(float(cnt * pixel_area_ha), 2)
        label_name = ESA_WORLDCOVER_CLASSES.get(cls_id, f"Unknown Class {cls_id}")

        class_breakdown[cls_id] = {
            "name": label_name,
            "pixel_count": cnt,
            "percentage": pct,
            "area_hectares": ha,
            "color": ESA_WORLDCOVER_COLORS.get(cls_id, "#808080")
        }

    return {
        "total_pixels": total_count,
        "valid_pixels": valid_count,
        "classes": class_breakdown
    }


def ingest_worldcover_labels(
    village,
    reference_raster_path=None,
    year=2021,
    output_dir=None,
    force_refresh=False
):
    """
    Complete end-to-end ESA WorldCover label acquisition & spatial alignment pipeline:
    1. STAC Discovery: Finds ESA WorldCover 10m tile covering the village.
    2. Precision Masking: Clips raster to the official PostGIS MultiPolygon boundary.
    3. Grid Alignment with Resampling.nearest: Reprojects and resamples the categorical
       labels to the exact UTM coordinate grid, 10.0m resolution, and affine transform
       of the existing Sentinel / DEM stack.
    4. Storage: Writes `worldcover_aligned.tif` (uint8, nodata=0) in the village's media folder.

    Args:
        village (Village|str|int): Target village model or identifier.
        reference_raster_path (str, optional): Explicit path to reference Sentinel/DEM raster.
        year (int): WorldCover edition (2021 or 2020).
        output_dir (str, optional): Custom output directory.
        force_refresh (bool): Re-acquire and re-align even if files exist on disk.

    Returns:
        dict: Ingestion manifest with file path, CRS, grid dimensions, and class distribution.
    """
    village_instance = resolve_village_instance(village)

    # 1. Resolve Storage Directories
    if not output_dir:
        output_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "worldcover", f"village_{village_instance.id}")
    os.makedirs(output_dir, exist_ok=True)

    aligned_output_path = os.path.join(output_dir, "worldcover_aligned.tif")

    # 2. Check Idempotency / Cache
    if not force_refresh and os.path.isfile(aligned_output_path):
        logger.info(f"Using cached WorldCover labels for '{village_instance.name}'.")
        with rasterio.open(aligned_output_path) as src:
            data = src.read(1)
            dist = calculate_class_distribution(data, pixel_size_meters=float(src.res[0]))
            return {
                "success": True,
                "cached": True,
                "village_id": village_instance.id,
                "village_name": village_instance.name,
                "district": village_instance.district,
                "state": village_instance.state,
                "collection": "esa-worldcover",
                "label_path": aligned_output_path,
                "width": src.width,
                "height": src.height,
                "crs": src.crs.to_string(),
                "resolution": (float(src.res[0]), float(src.res[1])),
                "distribution": dist,
                "tile_id": src.tags().get("TILE_ID", "cached")
            }

    # 3. Discover STAC WorldCover tile
    tiles = search_esa_worldcover_tiles(village_instance, year=year, sign_urls=True)
    if not tiles:
        raise ValueError(f"No ESA WorldCover tiles found intersecting '{village_instance.name}'.")

    primary_tile = tiles[0]
    source_url = primary_tile["data_url"]

    # 4. Resolve Spatial Reference Grid from Existing Sentinel / DEM Data
    sensor_type = "None"
    if not reference_raster_path:
        reference_raster_path, sensor_type = find_reference_sentinel_raster(village_instance)

    # 5. Open Remote WorldCover COG & Reference Grid
    with rasterio.open(source_url) as src_label:
        src_crs = src_label.crs
        src_transform = src_label.transform

        if reference_raster_path and os.path.isfile(reference_raster_path):
            with rasterio.open(reference_raster_path) as ref_src:
                ref_crs = ref_src.crs
                ref_transform = ref_src.transform
                ref_width = ref_src.width
                ref_height = ref_src.height
                ref_shape = (ref_height, ref_width)
                ref_res = (float(ref_src.res[0]), float(ref_src.res[1]))
                ref_meta = ref_src.meta.copy()
        else:
            # Fallback: compute dynamic UTM zone at 10.0m resolution from village boundary
            logger.info(f"No existing Sentinel raster found for '{village_instance.name}'. Computing dynamic UTM grid.")
            lng = village_instance.location.x
            utm_zone = int((lng + 180.0) / 6.0) + 1
            utm_srid = 32600 + utm_zone
            ref_crs = rasterio.crs.CRS.from_epsg(utm_srid)

            aoi_data = generate_village_monitoring_aoi(village_instance)
            shape_wgs84 = shapely.geometry.shape(aoi_data["geojson"])

            transformer = Transformer.from_crs("EPSG:4326", ref_crs, always_xy=True)
            transformed_geom = transform(transformer.transform, shape_wgs84)
            bounds = transformed_geom.bounds  # minx, miny, maxx, maxy

            ref_transform, ref_width, ref_height = calculate_default_transform(
                src_crs, ref_crs, src_label.width, src_label.height, *src_label.bounds, resolution=10.0
            )
            ref_shape = (ref_height, ref_width)
            ref_res = (10.0, 10.0)
            ref_meta = src_label.meta.copy()
            sensor_type = f"Dynamic UTM {utm_zone}N (10m)"

        # 6. Reproject to Reference Grid with Resampling.nearest (CRUCIAL FOR CATEGORICAL LABELS)
        aligned_labels = np.zeros(ref_shape, dtype=np.uint8)

        reproject(
            source=rasterio.band(src_label, 1),
            destination=aligned_labels,
            src_transform=src_transform,
            src_crs=src_crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            src_nodata=0,
            dst_nodata=0,
            resampling=Resampling.nearest  # STAMP: Nearest Neighbor preserves integer categorical IDs
        )

    # 7. Apply Village PostGIS MultiPolygon Boundary Mask
    aoi_data = generate_village_monitoring_aoi(village_instance)
    shape_obj = shapely.geometry.shape(aoi_data["geojson"])

    transformer = Transformer.from_crs("EPSG:4326", ref_crs, always_xy=True)
    transformed_boundary = transform(transformer.transform, shape_obj)

    # Boolean boundary mask (True inside boundary, False outside)
    inside_mask = geometry_mask(
        [transformed_boundary],
        out_shape=ref_shape,
        transform=ref_transform,
        invert=True,
        all_touched=True
    )
    aligned_labels[~inside_mask] = 0

    # 8. Save Final worldcover_aligned.tif GeoTIFF
    out_meta = {
        "driver": "GTiff",
        "dtype": "uint8",
        "nodata": 0,
        "width": ref_width,
        "height": ref_height,
        "count": 1,
        "crs": ref_crs,
        "transform": ref_transform,
        "compress": "deflate"
    }

    with rasterio.open(aligned_output_path, "w", **out_meta) as dst:
        dst.write(aligned_labels, 1)
        dst.update_tags(
            DATASET="ESA WorldCover 10m",
            PRODUCT_YEAR=str(year),
            TILE_ID=primary_tile["tile_id"],
            VARIABLE="Land Use / Land Cover (Ground Truth Mask)",
            PURPOSE="U-Net Machine Learning Semantic Segmentation Target (y)",
            RESAMPLING="Nearest Neighbor (Resampling.nearest)",
            VILLAGE=village_instance.name,
            REFERENCE_RASTER=os.path.basename(reference_raster_path) if reference_raster_path else "None"
        )

    # Also place a copy / symlink in the village's DEM and SAR folders for convenience
    dem_alt_path = os.path.join(settings.MEDIA_ROOT, "satellite", "dem", f"village_{village_instance.id}", "worldcover_aligned.tif")
    if os.path.isdir(os.path.dirname(dem_alt_path)) and not os.path.isfile(dem_alt_path):
        try:
            with open(aligned_output_path, "rb") as fsrc, open(dem_alt_path, "wb") as fdst:
                fdst.write(fsrc.read())
        except Exception:
            pass

    distribution = calculate_class_distribution(aligned_labels, pixel_size_meters=ref_res[0], nodata_val=0)

    logger.info(f"ESA WorldCover label acquisition complete for '{village_instance.name}'.")

    return {
        "success": True,
        "cached": False,
        "village_id": village_instance.id,
        "village_name": village_instance.name,
        "district": village_instance.district,
        "state": village_instance.state,
        "collection": "esa-worldcover",
        "label_path": aligned_output_path,
        "width": ref_width,
        "height": ref_height,
        "crs": ref_crs.to_string(),
        "resolution": ref_res,
        "aligned_to_sensor": sensor_type,
        "reference_raster": reference_raster_path,
        "distribution": distribution,
        "tile_id": primary_tile["tile_id"]
    }
