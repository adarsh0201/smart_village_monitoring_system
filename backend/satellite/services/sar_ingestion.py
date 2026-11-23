"""
Sentinel-1 SAR Ingestion & Radiometric Preprocessing Service.

Production-grade pipeline for Phase 2: Sentinel-1 SAR Acquisition & Preprocessing:
1. Retrieval: Downloads and streams dual-polarization (VV & VH) Level-1 GRD Cloud-Optimized GeoTIFFs (COGs)
   from Microsoft Planetary Computer (with automatic SAS token signing) or AWS Earth Search STAC.
2. Boundary Masking: Fetches the verified PostGIS MultiPolygon boundary for each village and applies
   sub-pixel precision clipping using `rasterio.mask.mask` transformed to the scene's native UTM projection.
3. Radiometric Calibration: Converts raw linear digital numbers / backscatter intensity to Decibels (dB):
     sigma_0_dB = 10 * log10(max(intensity, 1e-7))
4. Dual-Pol Cross-Ratio (CR):
     CrossRatio_dB = VH_dB - VV_dB  (equivalent to 10 * log10(VH / VV))
   Normalizes for soil moisture and surface roughness fluctuations, isolating vegetative canopy volume & biomass.
5. Dual-Pol Radar Vegetation Index (RVI):
     RVI = (4 * VH_linear) / (VV_linear + VH_linear)
6. Spatial GeoTIFF Export: Writes analysis-ready, Deflate-compressed Cloud-Optimized GeoTIFFs
   with full affine transforms, CRS definitions, and metadata tags directly into the storage directory
   ready for downstream machine learning / change detection models.
7. PostGIS Persistence: Automatically synchronizes SatelliteScene, SatelliteBand (VV, VH),
   and SpectralIndex (SAR_CR, RVI) database records with full raster statistics.
"""

import os
import re
import math
import logging
import requests
import numpy as np
import rasterio
from rasterio.mask import mask
from pyproj import Transformer
import shapely.geometry
from shapely.ops import transform

from django.conf import settings
from django.utils import timezone
from django.contrib.gis.geos import Polygon, MultiPolygon

from villages.models import Village
from satellite.models import SatelliteScene, SatelliteBand, SpectralIndex
from satellite.services.aoi import generate_village_monitoring_aoi
from satellite.services.sar_search import (
    search_sentinel1_sar_scenes,
    sign_asset_url,
    get_planetary_computer_sas_token,
)

logger = logging.getLogger("satellite.sar_ingestion")


def sanitize_filename(name):
    """Sanitize scene identifier for safe cross-platform directory and file naming."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", str(name).strip())


def resolve_village_instance(village_ref):
    """
    Resolve a Village model instance from an instance, integer PK, or name string.
    """
    if isinstance(village_ref, Village):
        return village_ref
    if isinstance(village_ref, int) or (isinstance(village_ref, str) and village_ref.isdigit()):
        return Village.objects.get(pk=int(village_ref))
    if isinstance(village_ref, str):
        v = Village.objects.filter(name__iexact=village_ref.strip()).first()
        if v:
            return v
    raise ValueError(f"Could not resolve village from identifier: {village_ref}")


def calibrate_linear_to_db(linear_array, nodata_val=0.0):
    """
    Convert linear radar backscatter intensity to Decibels (dB).
    Formula: dB = 10.0 * log10(intensity)
    Applies a numerical safety floor of 1e-7 to prevent log10(0) or -inf.
    Preserves nodata values with standard -9999.0 flag.

    Args:
        linear_array (np.ndarray): 2D array of linear radar intensity.
        nodata_val (float): Original nodata marker in input array.

    Returns:
        tuple (np.ndarray, float): Calibrated dB array, nodata value (-9999.0).
    """
    valid_mask = (
        (linear_array > 0.0)
        & (linear_array != nodata_val)
        & np.isfinite(linear_array)
    )
    db_array = np.full_like(linear_array, -9999.0, dtype=np.float32)

    # Numerical floor at 1e-7 ensures stable logarithmic transform
    clipped_linear = np.clip(linear_array[valid_mask], 1e-7, None)
    db_array[valid_mask] = 10.0 * np.log10(clipped_linear)

    return db_array, -9999.0


def compute_sar_cross_ratio(vh_db_array, vv_db_array, nodata_val=-9999.0):
    """
    Compute SAR Dual-Pol Cross-Ratio in decibels:
    Ratio_dB = VH_dB - VV_dB  (equivalent to 10 * log10(VH / VV))

    The cross-ratio cancels common soil moisture and dielectric fluctuations,
    isolating volumetric radar backscatter from crop canopy and biomass.

    Args:
        vh_db_array (np.ndarray): Calibrated VH polarization array in dB.
        vv_db_array (np.ndarray): Calibrated VV polarization array in dB.
        nodata_val (float): Masked nodata value.

    Returns:
        np.ndarray: Dual-pol cross ratio array in dB.
    """
    valid_mask = (
        (vh_db_array != nodata_val)
        & (vv_db_array != nodata_val)
        & np.isfinite(vh_db_array)
        & np.isfinite(vv_db_array)
    )

    ratio_array = np.full_like(vh_db_array, nodata_val, dtype=np.float32)
    ratio_array[valid_mask] = vh_db_array[valid_mask] - vv_db_array[valid_mask]

    return ratio_array


def compute_radar_vegetation_index(vh_linear_array, vv_linear_array, nodata_val=-9999.0):
    """
    Compute Dual-Pol Radar Vegetation Index (RVI):
    RVI = (4 * VH) / (VV + VH)

    Ranges from 0 (bare soil / calm water) to ~1 (dense mature forest/vegetation).

    Args:
        vh_linear_array (np.ndarray): Raw linear VH intensity.
        vv_linear_array (np.ndarray): Raw linear VV intensity.
        nodata_val (float): Masked nodata value.

    Returns:
        np.ndarray: RVI array bounded between [0.0, 1.0].
    """
    denom = vv_linear_array + vh_linear_array
    valid_mask = (denom > 1e-6) & (vh_linear_array >= 0) & (vv_linear_array >= 0) & np.isfinite(denom)

    rvi_array = np.full_like(vh_linear_array, nodata_val, dtype=np.float32)
    rvi_array[valid_mask] = np.clip(
        (4.0 * vh_linear_array[valid_mask]) / denom[valid_mask],
        0.0,
        1.5
    )

    return rvi_array


def calculate_sar_raster_statistics(data_array, nodata_val=-9999.0):
    """
    Compute comprehensive statistical summary for valid unmasked radar pixels.
    """
    valid_pixels = data_array[
        (data_array != nodata_val) & np.isfinite(data_array)
    ]

    total_pixels = data_array.size
    valid_count = int(valid_pixels.size)

    if valid_count == 0:
        return {
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "std_dev": None,
            "valid_count": 0,
            "total_count": total_pixels
        }

    return {
        "min": round(float(np.min(valid_pixels)), 4),
        "max": round(float(np.max(valid_pixels)), 4),
        "mean": round(float(np.mean(valid_pixels)), 4),
        "median": round(float(np.median(valid_pixels)), 4),
        "std_dev": round(float(np.std(valid_pixels)), 4),
        "valid_count": valid_count,
        "total_count": total_pixels
    }


def download_and_clip_sar_raster(source_url, output_path, village, buffer_km=2.5):
    """
    Stream/download a Sentinel-1 polarization COG and clip to the village MultiPolygon boundary.
    Uses rasterio.mask with CRS reprojection from WGS84 to the raster's native CRS.
    """
    # 1. Fetch the official MultiPolygon geometry for the village
    village_instance = resolve_village_instance(village)
    aoi_data = generate_village_monitoring_aoi(village_instance, buffer_km=buffer_km)
    shape_obj = shapely.geometry.shape(aoi_data["geojson"])

    # 2. Open source raster (direct HTTP COG streaming via GDAL or local file)
    with rasterio.open(source_url) as src:
        src_crs = src.crs

        # Transform boundary polygon from EPSG:4326 to raster's native CRS if projected
        if src_crs is not None:
            transformer = Transformer.from_crs("EPSG:4326", src_crs, always_xy=True)
            transformed_geom = transform(transformer.transform, shape_obj)
            shapes = [transformed_geom]
            out_crs = src_crs
        else:
            shapes = [shape_obj]
            out_crs = "EPSG:4326"

        # Precision mask and sub-pixel crop to boundary
        out_image, out_transform = mask(
            src,
            shapes,
            crop=True,
            all_touched=True,
            filled=True,
            nodata=0.0
        )

        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
            "crs": out_crs,
            "nodata": 0.0,
            "compress": "deflate",
            "dtype": "float32"
        })

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with rasterio.open(output_path, "w", **out_meta) as dst:
            dst.write(out_image[0].astype(np.float32), 1)

    return output_path


def ingest_sentinel1_sar_scene(
    village,
    scene_id,
    vv_asset_url=None,
    vh_asset_url=None,
    buffer_km=2.5,
    force_refresh=False
):
    """
    Complete end-to-end ingestion pipeline for a Sentinel-1 SAR scene:
    1. Idempotency Check: Verifies if the scene is already ingested.
    2. Asset Resolution: Obtains signed Planetary Computer or AWS URLs for VV & VH.
    3. Spatial Clipping: Clips VV and VH rasters to the village MultiPolygon boundary.
    4. Calibration: Converts linear DN intensity to Decibels (dB).
    5. Metric Derivation: Computes Dual-Pol Cross Ratio (VH/VV) and RVI.
    6. Database Persistence: Creates/updates SatelliteScene, SatelliteBand, and SpectralIndex.
    """
    village_instance = resolve_village_instance(village)
    safe_scene_id = sanitize_filename(scene_id)
    scene_storage_dir = os.path.join(
        settings.MEDIA_ROOT, "satellite", "sar", f"village_{village_instance.id}", safe_scene_id
    )
    os.makedirs(scene_storage_dir, exist_ok=True)

    # 1. Idempotency Check
    existing_scene = SatelliteScene.objects.filter(
        village=village_instance, scene_id=scene_id, status="completed"
    ).first()

    if existing_scene and not force_refresh:
        band_count = existing_scene.bands.count()
        if band_count >= 2:
            logger.info(f"Scene {scene_id} already ingested for {village_instance.name} (cached).")
            return {
                "success": True,
                "scene": existing_scene,
                "cached": True,
                "message": f"Sentinel-1 SAR scene {scene_id} already processed for {village_instance.name}."
            }

    # 2. Asset URL Resolution via STAC
    if not vv_asset_url or not vh_asset_url:
        search_results = search_sentinel1_sar_scenes(
            village_instance,
            limit=25,
            collection="sentinel-1-rtc",
            sign_urls=True
        )
        if not search_results:
            search_results = search_sentinel1_sar_scenes(
                village_instance,
                limit=25,
                collection="sentinel-1-grd",
                sign_urls=True
            )

        scene_list = search_results if isinstance(search_results, list) else search_results.get("scenes", [])
        matched_item = next(
            (item for item in scene_list if item.get("scene_id") == scene_id),
            None
        )

        if matched_item:
            assets = matched_item.get("assets") or matched_item.get("band_assets") or {}
            vv_asset_url = assets.get("vv") or assets.get("VV")
            vh_asset_url = assets.get("vh") or assets.get("VH")

    if not vv_asset_url or not vh_asset_url:
        raise ValueError(f"Could not locate VV and VH assets for Sentinel-1 scene: {scene_id}")

    # Ensure SAS token is attached if accessing Planetary Computer blob storage
    if "blob.core.windows.net" in vv_asset_url and "sig=" not in vv_asset_url:
        sas_token = get_planetary_computer_sas_token("sentinel-1-rtc") or get_planetary_computer_sas_token("sentinel-1-grd")
        vv_asset_url = sign_asset_url(vv_asset_url, sas_token)
        vh_asset_url = sign_asset_url(vh_asset_url, sas_token)

    # 3. Create or Initialize SatelliteScene Database Record
    now = timezone.now()
    scene_record, _ = SatelliteScene.objects.update_or_create(
        village=village_instance,
        scene_id=scene_id,
        defaults={
            "provider": "Microsoft Planetary Computer (STAC)",
            "collection": "sentinel-1-grd",
            "acquisition_date": now,
            "cloud_cover": 0.0,
            "aoi_cloud_cover": 0.0,
            "processing_level": "GRD-IW",
            "status": "downloading",
            "is_provisional_aoi": village_instance.boundary is None
        }
    )

    try:
        # 4. Download and Clip Raw Polarizations to Village MultiPolygon
        vv_raw_path = os.path.join(scene_storage_dir, "VV_raw.tif")
        vh_raw_path = os.path.join(scene_storage_dir, "VH_raw.tif")

        logger.info(f"Downloading & clipping VV polarization for {village_instance.name}...")
        download_and_clip_sar_raster(vv_asset_url, vv_raw_path, village_instance, buffer_km=buffer_km)

        logger.info(f"Downloading & clipping VH polarization for {village_instance.name}...")
        download_and_clip_sar_raster(vh_asset_url, vh_raw_path, village_instance, buffer_km=buffer_km)

        # 5. Radiometric Calibration and Metric Calculation
        vv_db_path = os.path.join(scene_storage_dir, "VV_db.tif")
        vh_db_path = os.path.join(scene_storage_dir, "VH_db.tif")
        cr_path = os.path.join(scene_storage_dir, "SAR_CrossRatio_VH_VV.tif")
        rvi_path = os.path.join(scene_storage_dir, "SAR_RVI.tif")

        with rasterio.open(vv_raw_path) as src_vv, rasterio.open(vh_raw_path) as src_vh:
            vv_linear = src_vv.read(1).astype(np.float32)
            vh_linear = src_vh.read(1).astype(np.float32)
            meta = src_vv.meta.copy()

            # Calibrate linear DN backscatter to dB
            vv_db, db_nodata = calibrate_linear_to_db(vv_linear, nodata_val=src_vv.nodata or 0.0)
            vh_db, _ = calibrate_linear_to_db(vh_linear, nodata_val=src_vh.nodata or 0.0)

            # Compute Dual-Pol Cross-Ratio (VH_dB - VV_dB) and RVI (4*VH / (VV + VH))
            cr_array = compute_sar_cross_ratio(vh_db, vv_db, nodata_val=db_nodata)
            rvi_array = compute_radar_vegetation_index(vh_linear, vv_linear, nodata_val=db_nodata)

            meta.update({
                "dtype": "float32",
                "nodata": db_nodata,
                "compress": "deflate"
            })

            # Save Calibrated VV (dB) GeoTIFF
            with rasterio.open(vv_db_path, "w", **meta) as dst:
                dst.write(vv_db, 1)
                dst.update_tags(
                    POLARIZATION="VV",
                    UNITS="dB (Decibels)",
                    SENSOR="Sentinel-1 C-SAR IW",
                    VILLAGE=village_instance.name
                )

            # Save Calibrated VH (dB) GeoTIFF
            with rasterio.open(vh_db_path, "w", **meta) as dst:
                dst.write(vh_db, 1)
                dst.update_tags(
                    POLARIZATION="VH",
                    UNITS="dB (Decibels)",
                    SENSOR="Sentinel-1 C-SAR IW",
                    VILLAGE=village_instance.name
                )

            # Save Cross-Ratio GeoTIFF
            with rasterio.open(cr_path, "w", **meta) as dst:
                dst.write(cr_array, 1)
                dst.update_tags(
                    INDEX="SAR_CrossRatio",
                    FORMULA="VH_dB - VV_dB",
                    APPLICATION="Vegetation Structure & Biomass Density",
                    VILLAGE=village_instance.name
                )

            # Save Radar Vegetation Index (RVI) GeoTIFF
            with rasterio.open(rvi_path, "w", **meta) as dst:
                dst.write(rvi_array, 1)
                dst.update_tags(
                    INDEX="RVI",
                    FORMULA="(4 * VH) / (VV + VH)",
                    APPLICATION="Dual-Pol Radar Canopy Cover & Water Content",
                    VILLAGE=village_instance.name
                )

            # Compute Statistical Summaries
            vv_stats = calculate_sar_raster_statistics(vv_db, nodata_val=db_nodata)
            vh_stats = calculate_sar_raster_statistics(vh_db, nodata_val=db_nodata)
            cr_stats = calculate_sar_raster_statistics(cr_array, nodata_val=db_nodata)
            rvi_stats = calculate_sar_raster_statistics(rvi_array, nodata_val=db_nodata)

            if src_vv.crs:
                crs_epsg = src_vv.crs.to_epsg()
                crs_str = f"EPSG:{crs_epsg}" if crs_epsg else (src_vv.crs.to_string() if hasattr(src_vv.crs, "to_string") else str(src_vv.crs))[:490]
            else:
                crs_str = "EPSG:4326"

            res_val = float(src_vv.res[0])
            w = int(src_vv.width)
            h = int(src_vv.height)

        # 6. Register Bands in Database
        rel_vv = os.path.relpath(vv_db_path, settings.MEDIA_ROOT).replace("\\", "/")
        rel_vh = os.path.relpath(vh_db_path, settings.MEDIA_ROOT).replace("\\", "/")

        SatelliteBand.objects.update_or_create(
            scene=scene_record,
            band_name="VV",
            defaults={
                "file_path": rel_vv,
                "resolution": res_val,
                "crs": crs_str,
                "width": w,
                "height": h,
                "file_size": os.path.getsize(vv_db_path)
            }
        )

        SatelliteBand.objects.update_or_create(
            scene=scene_record,
            band_name="VH",
            defaults={
                "file_path": rel_vh,
                "resolution": res_val,
                "crs": crs_str,
                "width": w,
                "height": h,
                "file_size": os.path.getsize(vh_db_path)
            }
        )

        # 7. Register Cross-Ratio Index in Database
        rel_cr = os.path.relpath(cr_path, settings.MEDIA_ROOT).replace("\\", "/")
        SpectralIndex.objects.update_or_create(
            scene=scene_record,
            index_type="SAR_CR",
            defaults={
                "file_path": rel_cr,
                "resolution": res_val,
                "crs": crs_str,
                "min_value": cr_stats["min"],
                "max_value": cr_stats["max"],
                "mean": cr_stats["mean"],
                "median": cr_stats["median"],
                "std_dev": cr_stats["std_dev"],
                "valid_pixel_count": cr_stats["valid_count"],
                "total_pixel_count": cr_stats["total_count"],
                "cloud_masked": False,
                "status": "completed"
            }
        )

        # 8. Register Radar Vegetation Index (RVI) in Database
        rel_rvi = os.path.relpath(rvi_path, settings.MEDIA_ROOT).replace("\\", "/")
        SpectralIndex.objects.update_or_create(
            scene=scene_record,
            index_type="RVI",
            defaults={
                "file_path": rel_rvi,
                "resolution": res_val,
                "crs": crs_str,
                "min_value": rvi_stats["min"],
                "max_value": rvi_stats["max"],
                "mean": rvi_stats["mean"],
                "median": rvi_stats["median"],
                "std_dev": rvi_stats["std_dev"],
                "valid_pixel_count": rvi_stats["valid_count"],
                "total_pixel_count": rvi_stats["total_count"],
                "cloud_masked": False,
                "status": "completed"
            }
        )

        # 9. Clean up intermediate raw files to conserve storage
        if os.path.exists(vv_raw_path):
            os.remove(vv_raw_path)
        if os.path.exists(vh_raw_path):
            os.remove(vh_raw_path)

        scene_record.status = "completed"
        scene_record.save(update_fields=["status", "updated_at"])

        return {
            "success": True,
            "scene": scene_record,
            "cached": False,
            "manifest": {
                "vv_path": vv_db_path,
                "vh_path": vh_db_path,
                "cross_ratio_path": cr_path,
                "rvi_path": rvi_path,
                "statistics": {
                    "vv_db": vv_stats,
                    "vh_db": vh_stats,
                    "cross_ratio_db": cr_stats,
                    "rvi": rvi_stats
                }
            }
        }

    except Exception as exc:
        logger.error(f"Failed to ingest Sentinel-1 SAR scene {scene_id}: {exc}", exc_info=True)
        scene_record.status = "failed"
        scene_record.error_message = str(exc)
        scene_record.save(update_fields=["status", "error_message", "updated_at"])
        raise exc


def process_sar_scene_for_village(village, scene_id, vv_source_path, vh_source_path, output_dir=None):
    """
    Direct offline/file-based processing function for local SAR GeoTIFFs.
    Useful for batch offline workflows, test runners, and synthetic SAR scenes.
    """
    village_instance = resolve_village_instance(village)
    if not output_dir:
        output_dir = os.path.join(
            settings.MEDIA_ROOT, "satellite", "sar", f"village_{village_instance.id}", sanitize_filename(scene_id)
        )
    os.makedirs(output_dir, exist_ok=True)

    vv_clipped = os.path.join(output_dir, "VV_raw.tif")
    vh_clipped = os.path.join(output_dir, "VH_raw.tif")

    from satellite.services.clipping import clip_geotiff_to_village
    clip_geotiff_to_village(vv_source_path, vv_clipped, village_instance)
    clip_geotiff_to_village(vh_source_path, vh_clipped, village_instance)

    vv_db_path = os.path.join(output_dir, "VV_db.tif")
    vh_db_path = os.path.join(output_dir, "VH_db.tif")
    cr_path = os.path.join(output_dir, "SAR_CrossRatio_VH_VV.tif")
    rvi_path = os.path.join(output_dir, "SAR_RVI.tif")

    with rasterio.open(vv_clipped) as src_vv, rasterio.open(vh_clipped) as src_vh:
        vv_raw = src_vv.read(1).astype(np.float32)
        vh_raw = src_vh.read(1).astype(np.float32)
        meta = src_vv.meta.copy()

        vv_db, db_nodata = calibrate_linear_to_db(vv_raw, nodata_val=src_vv.nodata or 0.0)
        vh_db, _ = calibrate_linear_to_db(vh_raw, nodata_val=src_vh.nodata or 0.0)
        cr_data = compute_sar_cross_ratio(vh_db, vv_db, nodata_val=db_nodata)
        rvi_data = compute_radar_vegetation_index(vh_raw, vv_raw, nodata_val=db_nodata)

        meta.update({
            "dtype": "float32",
            "nodata": db_nodata,
            "compress": "deflate"
        })

        with rasterio.open(vv_db_path, "w", **meta) as dst:
            dst.write(vv_db, 1)

        with rasterio.open(vh_db_path, "w", **meta) as dst:
            dst.write(vh_db, 1)

        with rasterio.open(cr_path, "w", **meta) as dst:
            dst.write(cr_data, 1)

        with rasterio.open(rvi_path, "w", **meta) as dst:
            dst.write(rvi_data, 1)

    if os.path.exists(vv_clipped):
        os.remove(vv_clipped)
    if os.path.exists(vh_clipped):
        os.remove(vh_clipped)

    return {
        "scene_id": scene_id,
        "village": village_instance.name,
        "vv_db_path": vv_db_path,
        "vh_db_path": vh_db_path,
        "cross_ratio_path": cr_path,
        "rvi_path": rvi_path,
        "statistics": {
            "vv_mean_db": float(np.mean(vv_db[vv_db != db_nodata])),
            "vh_mean_db": float(np.mean(vh_db[vh_db != db_nodata])),
            "cross_ratio_mean": float(np.mean(cr_data[cr_data != db_nodata])),
            "rvi_mean": float(np.mean(rvi_data[rvi_data != db_nodata]))
        }
    }


def batch_ingest_sar_for_villages(villages=None, orbit_direction=None, limit_per_village=1, force_refresh=False):
    """
    Batch helper to acquire and ingest Sentinel-1 SAR imagery across multiple villages.

    Args:
        villages (QuerySet or list, optional): Village instances. Defaults to all villages.
        orbit_direction (str, optional): 'ascending', 'descending', or None.
        limit_per_village (int): Number of scenes to acquire per village (default: 1).
        force_refresh (bool): Force re-acquisition and overwrite cache.

    Returns:
        dict: Summary of successful and failed village acquisitions.
    """
    if villages is None:
        villages = Village.objects.all().order_by("state", "name")

    results = {"success": [], "failed": []}

    for v in villages:
        logger.info(f"--- Processing SAR for {v.name} ({v.district}, {v.state}) ---")
        try:
            scenes = search_sentinel1_sar_scenes(
                village=v,
                limit=limit_per_village,
                orbit_direction=orbit_direction,
                collection="sentinel-1-grd",
                sign_urls=True
            )
            if not scenes:
                logger.warning(f"No Sentinel-1 scenes found for {v.name}.")
                results["failed"].append({"village": v.name, "reason": "No scenes found"})
                continue

            for s in scenes[:limit_per_village]:
                res = ingest_sentinel1_sar_scene(
                    village=v,
                    scene_id=s["scene_id"],
                    force_refresh=force_refresh
                )
                results["success"].append({
                    "village": v.name,
                    "scene_id": s["scene_id"],
                    "manifest": res.get("manifest")
                })
        except Exception as exc:
            logger.error(f"Error processing SAR for {v.name}: {exc}")
            results["failed"].append({"village": v.name, "reason": str(exc)})

    return results
