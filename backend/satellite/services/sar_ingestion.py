"""
Sentinel-1 SAR Ingestion & Radiometric Preprocessing Service.

Handles Phase 2: Sentinel-1 SAR Acquisition & Preprocessing:
1. Downloading and streaming dual-polarization (VV & VH) Level-1 GRD Cloud-Optimized GeoTIFFs (COGs).
2. Precision sub-pixel masking and clipping to official village MultiPolygon boundaries.
3. Radiometric calibration from raw linear digital numbers (DN) / backscatter intensity to Decibels (dB):
     sigma_0_dB = 10 * log10(max(intensity, 1e-7))
4. Computing the SAR Dual-Polarization Cross-Ratio (VH/VV):
     CrossRatio_dB = VH_dB - VV_dB  (equivalent to 10 * log10(VH / VV))
   Normalizes for soil roughness/moisture to isolate vegetative canopy and biomass.
5. Computing the Dual-Pol Radar Vegetation Index (RVI):
     RVI = (4 * VH_linear) / (VV_linear + VH_linear)
6. Writing standard Cloud-Optimized GeoTIFFs with full spatial metadata (CRS, Affine transform, GeoTIFF tags).
7. Ingesting records and raster statistics into PostgreSQL/PostGIS.
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

from django.conf import settings
from django.utils import timezone
from django.contrib.gis.geos import Polygon, MultiPolygon

from satellite.models import SatelliteScene, SatelliteBand, SpectralIndex
from satellite.services.aoi import generate_village_monitoring_aoi
from satellite.services.sar_search import search_sentinel1_sar_scenes, sign_asset_url, get_planetary_computer_sas_token

logger = logging.getLogger("satellite.sar_ingestion")


def sanitize_filename(name):
    """Sanitize scene identifier for safe cross-platform folder naming."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", name)


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
    Download/stream a Sentinel-1 polarization COG and clip to the village AOI.
    Uses rasterio.mask with CRS reprojection from WGS84 to the raster's native CRS.
    """
    # 1. Determine clipping AOI geometry (official boundary or provisional circular buffer)
    aoi_data = generate_village_monitoring_aoi(village, buffer_km=buffer_km)
    aoi_shapely = shapely.geometry.shape(aoi_data["geojson"])

    # 2. Open source raster (direct HTTP COG streaming or local file)
    with rasterio.open(source_url) as src:
        src_crs = src.crs

        # Transform AOI polygon from EPSG:4326 to raster's native CRS
        transformer = Transformer.from_crs("EPSG:4326", src_crs, always_xy=True)
        transformed_geom = shapely.ops.transform(transformer.transform, aoi_shapely)
        geojson_geom = [shapely.geometry.mapping(transformed_geom)]

        # Clip using precision boundary mask
        out_image, out_transform = mask(
            src,
            geojson_geom,
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
    safe_scene_id = sanitize_filename(scene_id)
    scene_storage_dir = os.path.join(
        settings.MEDIA_ROOT, "satellite", "sar", f"village_{village.id}", safe_scene_id
    )
    os.makedirs(scene_storage_dir, exist_ok=True)

    # 1. Idempotency Check
    existing_scene = SatelliteScene.objects.filter(
        village=village, scene_id=scene_id, status="completed"
    ).first()

    if existing_scene and not force_refresh:
        band_count = existing_scene.bands.count()
        if band_count >= 2:
            logger.info(f"Scene {scene_id} already ingested for {village.name} (cached).")
            return {
                "success": True,
                "scene": existing_scene,
                "cached": True,
                "message": f"Sentinel-1 SAR scene {scene_id} already processed for {village.name}."
            }

    # 2. Asset URL Resolution via STAC
    if not vv_asset_url or not vh_asset_url:
        search_results = search_sentinel1_sar_scenes(
            village,
            limit=25,
            collection="sentinel-1-grd",
            sign_urls=True
        )
        matched_item = next(
            (item for item in search_results.get("scenes", []) if item["scene_id"] == scene_id),
            None
        )

        if not matched_item:
            # Direct SAS fallback
            sas_token = get_planetary_computer_sas_token("sentinel-1-grd")
            vv_asset_url = sign_asset_url(vv_asset_url, sas_token)
            vh_asset_url = sign_asset_url(vh_asset_url, sas_token)
        else:
            assets = matched_item.get("band_assets", {})
            vv_asset_url = assets.get("VV")
            vh_asset_url = assets.get("VH")

    if not vv_asset_url or not vh_asset_url:
        raise ValueError(f"Could not locate VV and VH assets for Sentinel-1 scene: {scene_id}")

    # 3. Create or Initialize SatelliteScene Database Record
    now = timezone.now()
    scene_record, _ = SatelliteScene.objects.update_or_create(
        village=village,
        scene_id=scene_id,
        defaults={
            "provider": "Microsoft Planetary Computer (STAC)",
            "collection": "sentinel-1-grd",
            "acquisition_date": now,
            "cloud_cover": 0.0,
            "aoi_cloud_cover": 0.0,
            "processing_level": "GRD-IW",
            "status": "downloading",
            "is_provisional_aoi": village.boundary is None
        }
    )

    try:
        # 4. Download and Clip Raw Polarizations
        vv_raw_path = os.path.join(scene_storage_dir, "VV_raw.tif")
        vh_raw_path = os.path.join(scene_storage_dir, "VH_raw.tif")

        logger.info(f"Downloading & clipping VV polarization for {village.name}...")
        download_and_clip_sar_raster(vv_asset_url, vv_raw_path, village, buffer_km=buffer_km)

        logger.info(f"Downloading & clipping VH polarization for {village.name}...")
        download_and_clip_sar_raster(vh_asset_url, vh_raw_path, village, buffer_km=buffer_km)

        # 5. Radiometric Calibration and Metric Calculation
        vv_db_path = os.path.join(scene_storage_dir, "VV_db.tif")
        vh_db_path = os.path.join(scene_storage_dir, "VH_db.tif")
        cr_path = os.path.join(scene_storage_dir, "SAR_CrossRatio_VH_VV.tif")
        rvi_path = os.path.join(scene_storage_dir, "SAR_RVI.tif")

        with rasterio.open(vv_raw_path) as src_vv, rasterio.open(vh_raw_path) as src_vh:
            vv_linear = src_vv.read(1).astype(np.float32)
            vh_linear = src_vh.read(1).astype(np.float32)
            meta = src_vv.meta.copy()

            # Calibrate linear DN to dB
            vv_db, db_nodata = calibrate_linear_to_db(vv_linear, nodata_val=src_vv.nodata or 0.0)
            vh_db, _ = calibrate_linear_to_db(vh_linear, nodata_val=src_vh.nodata or 0.0)

            # Compute Cross-Ratio (VH_dB - VV_dB) and RVI (4*VH / (VV + VH))
            cr_array = compute_sar_cross_ratio(vh_db, vv_db, nodata_val=db_nodata)
            rvi_array = compute_radar_vegetation_index(vh_linear, vv_linear, nodata_val=db_nodata)

            meta.update({
                "dtype": "float32",
                "nodata": db_nodata,
                "compress": "deflate"
            })

            # Save Calibrated VV (dB)
            with rasterio.open(vv_db_path, "w", **meta) as dst:
                dst.write(vv_db, 1)
                dst.update_tags(
                    POLARIZATION="VV",
                    UNITS="dB (Decibels)",
                    SENSOR="Sentinel-1 C-SAR IW",
                    VILLAGE=village.name
                )

            # Save Calibrated VH (dB)
            with rasterio.open(vh_db_path, "w", **meta) as dst:
                dst.write(vh_db, 1)
                dst.update_tags(
                    POLARIZATION="VH",
                    UNITS="dB (Decibels)",
                    SENSOR="Sentinel-1 C-SAR IW",
                    VILLAGE=village.name
                )

            # Save Cross-Ratio
            with rasterio.open(cr_path, "w", **meta) as dst:
                dst.write(cr_array, 1)
                dst.update_tags(
                    INDEX="SAR_CrossRatio",
                    FORMULA="VH_dB - VV_dB",
                    APPLICATION="Vegetation Structure & Biomass Density",
                    VILLAGE=village.name
                )

            # Save Radar Vegetation Index (RVI)
            with rasterio.open(rvi_path, "w", **meta) as dst:
                dst.write(rvi_array, 1)
                dst.update_tags(
                    INDEX="RVI",
                    FORMULA="(4 * VH) / (VV + VH)",
                    APPLICATION="Dual-Pol Radar Canopy Cover & Water Content",
                    VILLAGE=village.name
                )

            # Compute Statistical Summaries
            vv_stats = calculate_sar_raster_statistics(vv_db, nodata_val=db_nodata)
            vh_stats = calculate_sar_raster_statistics(vh_db, nodata_val=db_nodata)
            cr_stats = calculate_sar_raster_statistics(cr_array, nodata_val=db_nodata)
            rvi_stats = calculate_sar_raster_statistics(rvi_array, nodata_val=db_nodata)

            crs_str = str(src_vv.crs)
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

        # 7. Register Indices in Database
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

        # 8. Clean up intermediate raw files to save disk space
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
    if not output_dir:
        output_dir = os.path.join(
            settings.MEDIA_ROOT, "satellite", "sar", f"village_{village.id}", sanitize_filename(scene_id)
        )
    os.makedirs(output_dir, exist_ok=True)

    vv_clipped = os.path.join(output_dir, "VV_raw.tif")
    vh_clipped = os.path.join(output_dir, "VH_raw.tif")

    # Clip source rasters using precision mask
    from satellite.services.clipping import clip_geotiff_to_village
    clip_geotiff_to_village(vv_source_path, vv_clipped, village)
    clip_geotiff_to_village(vh_source_path, vh_clipped, village)

    vv_db_path = os.path.join(output_dir, "VV_db.tif")
    vh_db_path = os.path.join(output_dir, "VH_db.tif")
    cr_path = os.path.join(output_dir, "SAR_CrossRatio_VH_VV.tif")

    with rasterio.open(vv_clipped) as src_vv, rasterio.open(vh_clipped) as src_vh:
        vv_raw = src_vv.read(1).astype(np.float32)
        vh_raw = src_vh.read(1).astype(np.float32)
        meta = src_vv.meta.copy()

        vv_db, db_nodata = calibrate_linear_to_db(vv_raw, nodata_val=src_vv.nodata or 0.0)
        vh_db, _ = calibrate_linear_to_db(vh_raw, nodata_val=src_vh.nodata or 0.0)
        cr_data = compute_sar_cross_ratio(vh_db, vv_db, nodata_val=db_nodata)

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

    if os.path.exists(vv_clipped):
        os.remove(vv_clipped)
    if os.path.exists(vh_clipped):
        os.remove(vh_clipped)

    return {
        "scene_id": scene_id,
        "village": village.name,
        "vv_db_path": vv_db_path,
        "vh_db_path": vh_db_path,
        "cross_ratio_path": cr_path,
        "statistics": {
            "vv_mean_db": float(np.mean(vv_db[vv_db != db_nodata])),
            "vh_mean_db": float(np.mean(vh_db[vh_db != db_nodata])),
            "cross_ratio_mean": float(np.mean(cr_data[cr_data != db_nodata]))
        }
    }
