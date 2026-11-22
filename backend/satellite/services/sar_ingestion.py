"""
Sentinel-1 SAR Ingestion & Radiometric Preprocessing Service.

Handles:
- Downloading VV & VH polarization GeoTIFFs for an acquired Sentinel-1 scene.
- Precision masking/clipping to the village MultiPolygon boundary using rasterio.mask.
- Radiometric calibration: Linear amplitude / intensity to Decibels (dB):
    dB = 10 * log10(max(intensity, 1e-7))
- Computing the Dual-Polarization Cross Ratio (VH / VV) for radar biomass
  and moisture assessment.
- Writing output GeoTIFFs with full spatial metadata, CRS, and affine transforms.
"""

import os
import logging
import numpy as np
import rasterio
from django.conf import settings
from satellite.services.clipping import clip_geotiff_to_village

logger = logging.getLogger("satellite.sar_ingestion")
RASTERIO_PROJ_DIR = os.path.join(os.path.dirname(rasterio.__file__), "proj_data")


def calibrate_linear_to_db(linear_array, nodata_val=0.0):
    """
    Convert linear radar backscatter intensity to Decibels (dB).
    dB = 10 * log10(intensity)
    Preserves nodata values.
    """
    valid_mask = (linear_array > 0) & (linear_array != nodata_val) & np.isfinite(linear_array)
    db_array = np.full_like(linear_array, -9999.0, dtype=np.float32)

    # 10 * log10 with numerical safety floor
    clipped_linear = np.clip(linear_array[valid_mask], 1e-7, None)
    db_array[valid_mask] = 10.0 * np.log10(clipped_linear)

    return db_array, -9999.0


def compute_sar_cross_ratio(vh_db_array, vv_db_array, nodata_val=-9999.0):
    """
    Compute SAR Dual-Pol Cross-Ratio in decibels:
    Ratio_dB = VH_dB - VV_dB  (equivalent to 10 * log10(VH / VV))
    Used for vegetation structure and biomass estimation.
    """
    valid_mask = (vh_db_array != nodata_val) & (vv_db_array != nodata_val) & \
                 np.isfinite(vh_db_array) & np.isfinite(vv_db_array)

    ratio_array = np.full_like(vh_db_array, nodata_val, dtype=np.float32)
    ratio_array[valid_mask] = vh_db_array[valid_mask] - vv_db_array[valid_mask]

    return ratio_array


def process_sar_scene_for_village(village, scene_id, vv_source_path, vh_source_path, output_dir=None):
    """
    Full processing pipeline for a Sentinel-1 scene clipped to a village:
    1. Clips raw VV and VH rasters to official village MultiPolygon.
    2. Calibrates raw values to backscatter coefficient (dB).
    3. Calculates Dual-Pol VH/VV Cross-Ratio raster.
    4. Writes GeoTIFFs and returns file manifests.
    """
    if not output_dir:
        output_dir = os.path.join(
            settings.MEDIA_ROOT, "satellite", "sar", str(village.id), scene_id
        )
    os.makedirs(output_dir, exist_ok=True)

    # 1. Clip VV raster
    vv_raw_clipped = os.path.join(output_dir, "VV_raw.tif")
    vh_raw_clipped = os.path.join(output_dir, "VH_raw.tif")

    clip_geotiff_to_village(vv_source_path, vv_raw_clipped, village)
    clip_geotiff_to_village(vh_source_path, vh_raw_clipped, village)

    # 2. Calibrate to Decibels (dB)
    vv_db_path = os.path.join(output_dir, "VV_db.tif")
    vh_db_path = os.path.join(output_dir, "VH_db.tif")
    ratio_path = os.path.join(output_dir, "SAR_CrossRatio_VH_VV.tif")

    with rasterio.open(vv_raw_clipped) as src_vv, rasterio.open(vh_raw_clipped) as src_vh:
        vv_data = src_vv.read(1).astype(np.float32)
        vh_data = src_vh.read(1).astype(np.float32)
        meta = src_vv.meta.copy()

        # Convert to dB
        vv_db, db_nodata = calibrate_linear_to_db(vv_data, nodata_val=src_vv.nodata or 0.0)
        vh_db, _ = calibrate_linear_to_db(vh_data, nodata_val=src_vh.nodata or 0.0)

        # Cross Ratio (VH - VV in dB)
        cr_data = compute_sar_cross_ratio(vh_db, vv_db, nodata_val=db_nodata)

        meta.update({
            "dtype": "float32",
            "nodata": db_nodata,
            "compress": "deflate"
        })

        # Write VV (dB)
        with rasterio.open(vv_db_path, "w", **meta) as dst:
            dst.write(vv_db, 1)
            dst.update_tags(
                POLARIZATION="VV",
                UNITS="dB (Decibels)",
                SENSOR="Sentinel-1 SAR C-band",
                VILLAGE=village.name
            )

        # Write VH (dB)
        with rasterio.open(vh_db_path, "w", **meta) as dst:
            dst.write(vh_db, 1)
            dst.update_tags(
                POLARIZATION="VH",
                UNITS="dB (Decibels)",
                SENSOR="Sentinel-1 SAR C-band",
                VILLAGE=village.name
            )

        # Write Cross-Ratio
        with rasterio.open(ratio_path, "w", **meta) as dst:
            dst.write(cr_data, 1)
            dst.update_tags(
                INDEX="SAR_CrossRatio",
                FORMULA="VH_dB - VV_dB",
                APPLICATION="Radar Vegetation / Biomass / Soil Moisture Index",
                VILLAGE=village.name
            )

    # Clean up intermediate raw files
    if os.path.exists(vv_raw_clipped):
        os.remove(vv_raw_clipped)
    if os.path.exists(vh_raw_clipped):
        os.remove(vh_raw_clipped)

    logger.info(f"Successfully processed Sentinel-1 SAR products for '{village.name}' (Scene: {scene_id})")

    return {
        "scene_id": scene_id,
        "village": village.name,
        "vv_db_path": vv_db_path,
        "vh_db_path": vh_db_path,
        "cross_ratio_path": ratio_path,
        "statistics": {
            "vv_mean_db": float(np.mean(vv_db[vv_db != db_nodata])),
            "vh_mean_db": float(np.mean(vh_db[vh_db != db_nodata])),
            "cross_ratio_mean": float(np.mean(cr_data[cr_data != db_nodata]))
        }
    }

