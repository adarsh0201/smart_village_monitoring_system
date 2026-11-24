"""
Pixel-Wise Random Forest Classifier for Land Use / Land Cover (LULC).
Phase 8: Optical Feature Fusion (SAR + DEM + Sentinel-2 Optical NDVI / NDWI / SCL).

Integrates multi-sensor feature rasters and ground truth masks:
1. Feature Layers:
   - Sentinel-1 SAR Dual-Pol Backscatter (VV_db.tif, VH_db.tif in dB)
   - Copernicus DEM 30m Elevation (elevation_aligned.tif in meters)
   - Topographic Slope (slope_aligned.tif in degrees)
   - Sentinel-2 Optical Indices (NDVI.tif, NDWI.tif in [-1.0, 1.0])
   - Sentinel-2 Scene Classification Layer (SCL.tif for cloud/shadow masking)
2. Ground Truth Target Mask:
   - ESA WorldCover 10m Ground Truth (worldcover_aligned.tif)
3. Cloud Masking (-9999 Strategy):
   - Identifies pixels where SCL indicates clouds, cloud shadows, or defective pixels (0, 3, 8, 9, 10).
   - Overwrites NDVI and NDWI with -9999.0 at these indices.
   - Keeps these rows intact so Random Forest learns to fall back to SAR and DEM.
4. Preprocessing:
   - Spatial unrolling / flattening to tabular matrix: X in R^{N x 6}, y in R^{N}
   - Data cleaning: Filters out nodata cells (y == 0, background outside village boundary)
5. Training & Validation:
   - Stratified Train / Test split (80/20)
   - Multi-class Random Forest with 6-feature stack: [VV_db, VH_db, Elevation, Slope, NDVI, NDWI]
6. Model Persistence & Map Inference:
   - Saves trained model to backend/ml/models/rf_lulc.joblib
   - Generates full-coverage prediction GeoTIFF rf_predicted_lulc.tif
"""

import os
import re
import sys
import json
import logging
import argparse
from types import SimpleNamespace

import joblib
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

# Ensure rasterio PROJ data directory takes precedence over system/postgis PROJ
RASTERIO_PROJ_DATA = os.path.join(os.path.dirname(rasterio.__file__), "proj_data")
if os.path.isdir(RASTERIO_PROJ_DATA):
    os.environ["PROJ_LIB"] = RASTERIO_PROJ_DATA
    os.environ["PROJ_DATA"] = RASTERIO_PROJ_DATA

logger = logging.getLogger("ml.train_rf")

# Official ESA WorldCover Class Legend
LULC_CLASS_NAMES = {
    10: "Tree cover",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up",
    60: "Bare / sparse veg",
    70: "Snow and ice",
    80: "Permanent water",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen",
}

# 6-Feature Stack: SAR Dual-Pol, Topography, and Optical Spectral Indices
FEATURE_NAMES = ["VV_db", "VH_db", "Elevation", "Slope", "NDVI", "NDWI"]


def get_base_and_media_dirs():
    """Resolve BASE_DIR and MEDIA_ROOT safely with or without Django settings configured."""
    try:
        from django.conf import settings
        if settings.configured:
            return settings.BASE_DIR, settings.MEDIA_ROOT
    except Exception:
        pass

    # Fallback to filesystem hierarchy relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.abspath(os.path.join(script_dir, ".."))
    media_dir = os.path.join(backend_dir, "media")
    return backend_dir, media_dir


def resolve_village_instance(village_ref):
    """
    Resolve a Village instance from an object, integer PK, or name string.
    Gracefully falls back to a proxy instance when the database is unreachable.
    """
    if hasattr(village_ref, "id") and hasattr(village_ref, "name"):
        return village_ref

    base_dir, media_dir = get_base_and_media_dirs()

    # Attempt Django ORM lookup first
    try:
        from villages.models import Village
        if isinstance(village_ref, int) or (isinstance(village_ref, str) and str(village_ref).isdigit()):
            return Village.objects.get(pk=int(village_ref))
        if isinstance(village_ref, str):
            v = Village.objects.filter(name__iexact=village_ref.strip()).first()
            if v:
                return v
    except Exception as exc:
        logger.debug(f"Django ORM lookup failed ({exc}), falling back to filesystem proxy.")

    # Filesystem / Directory proxy fallback
    target_str = str(village_ref).strip()
    dem_parent = os.path.join(media_dir, "satellite", "dem")

    if target_str.isdigit():
        v_id = int(target_str)
        return SimpleNamespace(id=v_id, name=f"Village_{v_id}", district="Unknown", state="Uttar Pradesh")

    if target_str.lower() == "gahmar":
        return SimpleNamespace(id=22, name="Gahmar", district="Ghazipur", state="Uttar Pradesh")

    # Search media/satellite/dem/village_<id>
    if os.path.isdir(dem_parent):
        for folder in os.listdir(dem_parent):
            if folder.startswith("village_"):
                v_id = int(folder.replace("village_", ""))
                return SimpleNamespace(id=v_id, name=target_str, district="Unknown", state="Uttar Pradesh")

    raise ValueError(f"Could not resolve village from identifier: {village_ref}")


def read_and_align_band(src_ds, ref_shape, ref_transform, ref_crs, is_categorical=False):
    """
    Read raster data from an open rasterio dataset and align it to reference dimensions and CRS.
    Uses nearest-neighbor for categorical masks (SCL) and bilinear for continuous indices (NDVI, NDWI).
    """
    if src_ds.shape == ref_shape and src_ds.crs == ref_crs and src_ds.transform == ref_transform:
        return src_ds.read(1)

    dst_nodata = 0 if is_categorical else -9999.0
    dst_dtype = np.uint8 if is_categorical else np.float32
    aligned = np.full(ref_shape, dst_nodata, dtype=dst_dtype)

    reproject(
        source=rasterio.band(src_ds, 1),
        destination=aligned,
        src_transform=src_ds.transform,
        src_crs=src_ds.crs,
        dst_transform=ref_transform,
        dst_crs=ref_crs,
        resampling=Resampling.nearest if is_categorical else Resampling.bilinear,
        dst_nodata=dst_nodata
    )
    return aligned


def derive_and_align_optical_indices(village, s2_raw_dir, ref_raster_path, optical_dir):
    """
    Derive Sentinel-2 NDVI.tif, NDWI.tif, and SCL.tif from raw Level-2A bands (B08, B04, B03, SCL)
    and align them precisely to the village reference grid (10m UTM).
    """
    v = resolve_village_instance(village)
    os.makedirs(optical_dir, exist_ok=True)

    ndvi_out = os.path.join(optical_dir, "NDVI.tif")
    ndwi_out = os.path.join(optical_dir, "NDWI.tif")
    scl_out = os.path.join(optical_dir, "SCL.tif")

    if os.path.isfile(ndvi_out) and os.path.isfile(ndwi_out) and os.path.isfile(scl_out):
        return {"ndvi": ndvi_out, "ndwi": ndwi_out, "scl": scl_out}

    # Locate cleanest Sentinel-2 granule containing required bands
    candidate_scenes = []
    for entry in sorted(os.listdir(s2_raw_dir), reverse=True):
        full_p = os.path.join(s2_raw_dir, entry)
        if os.path.isdir(full_p):
            files = os.listdir(full_p)
            if all(b in files for b in ("B08.tif", "B04.tif", "B03.tif", "SCL.tif")):
                candidate_scenes.append(full_p)

    if not candidate_scenes:
        raise FileNotFoundError(
            f"No complete Sentinel-2 granule (B08, B04, B03, SCL) found in {s2_raw_dir}."
        )

    scene_path = candidate_scenes[0]

    with rasterio.open(ref_raster_path) as ref:
        ref_shape = ref.shape
        ref_crs = ref.crs
        ref_transform = ref.transform
        meta_float = ref.meta.copy()
        meta_byte = ref.meta.copy()

    meta_float.update(dtype="float32", nodata=-9999.0, count=1, compress="deflate")
    meta_byte.update(dtype="uint8", nodata=0, count=1, compress="deflate")

    with rasterio.open(os.path.join(scene_path, "B08.tif")) as f_b8, \
         rasterio.open(os.path.join(scene_path, "B04.tif")) as f_b4, \
         rasterio.open(os.path.join(scene_path, "B03.tif")) as f_b3, \
         rasterio.open(os.path.join(scene_path, "SCL.tif")) as f_scl:

        b8 = f_b8.read(1).astype(np.float32)
        b4 = f_b4.read(1).astype(np.float32)
        b3 = f_b3.read(1).astype(np.float32)
        scl = f_scl.read(1).astype(np.uint8)

        # 1. NDVI = (B08 - B04) / (B08 + B04)
        denom_ndvi = b8 + b4
        with np.errstate(divide="ignore", invalid="ignore"):
            ndvi_raw = np.where(denom_ndvi > 0, (b8 - b4) / denom_ndvi, -9999.0)
            ndvi_raw[~np.isfinite(ndvi_raw)] = -9999.0

        ndvi_aligned = np.full(ref_shape, -9999.0, dtype=np.float32)
        reproject(
            source=ndvi_raw,
            destination=ndvi_aligned,
            src_transform=f_b8.transform,
            src_crs=f_b8.crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=Resampling.bilinear,
            dst_nodata=-9999.0
        )

        # 2. NDWI (McFeeters) = (B03 - B08) / (B03 + B08)
        denom_ndwi = b3 + b8
        with np.errstate(divide="ignore", invalid="ignore"):
            ndwi_raw = np.where(denom_ndwi > 0, (b3 - b8) / denom_ndwi, -9999.0)
            ndwi_raw[~np.isfinite(ndwi_raw)] = -9999.0

        ndwi_aligned = np.full(ref_shape, -9999.0, dtype=np.float32)
        reproject(
            source=ndwi_raw,
            destination=ndwi_aligned,
            src_transform=f_b3.transform,
            src_crs=f_b3.crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=Resampling.bilinear,
            dst_nodata=-9999.0
        )

        # 3. SCL (Scene Classification Layer: 20m -> 10m nearest-neighbor)
        scl_aligned = np.zeros(ref_shape, dtype=np.uint8)
        reproject(
            source=scl,
            destination=scl_aligned,
            src_transform=f_scl.transform,
            src_crs=f_scl.crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=Resampling.nearest,
            dst_nodata=0
        )

    with rasterio.open(ndvi_out, "w", **meta_float) as dst:
        dst.write(ndvi_aligned, 1)
        dst.update_tags(VARIABLE="NDVI", SOURCE=os.path.basename(scene_path))

    with rasterio.open(ndwi_out, "w", **meta_float) as dst:
        dst.write(ndwi_aligned, 1)
        dst.update_tags(VARIABLE="NDWI", SOURCE=os.path.basename(scene_path))

    with rasterio.open(scl_out, "w", **meta_byte) as dst:
        dst.write(scl_aligned, 1)
        dst.update_tags(VARIABLE="SCL", SOURCE=os.path.basename(scene_path))

    logger.info(f"Derived and saved optical rasters in {optical_dir}")
    return {"ndvi": ndvi_out, "ndwi": ndwi_out, "scl": scl_out}


def find_village_raster_assets(village):
    """
    Locate the required feature rasters and ground truth mask for a village:
    - worldcover_aligned.tif (ESA WorldCover 10m Ground Truth)
    - elevation_aligned.tif & slope_aligned.tif (Copernicus DEM 30m)
    - VV_db.tif & VH_db.tif (Sentinel-1 SAR)
    - NDVI.tif, NDWI.tif & SCL.tif (Sentinel-2 Optical & Cloud Mask)
    """
    v = resolve_village_instance(village)
    base_dir, media_dir = get_base_and_media_dirs()

    # 1. WorldCover Target Mask
    wc_candidates = [
        os.path.join(media_dir, "satellite", "worldcover", f"village_{v.id}", "worldcover_aligned.tif"),
        os.path.join(media_dir, "satellite", "dem", f"village_{v.id}", "worldcover_aligned.tif"),
    ]
    wc_path = next((p for p in wc_candidates if os.path.isfile(p)), None)

    # 2. Topography: Elevation & Slope
    dem_dir = os.path.join(media_dir, "satellite", "dem", f"village_{v.id}")
    elev_path = os.path.join(dem_dir, "elevation_aligned.tif")
    slope_path = os.path.join(dem_dir, "slope_aligned.tif")

    # 3. Sentinel-1 SAR: VV & VH
    sar_dir = os.path.join(media_dir, "satellite", "sar", f"village_{v.id}")
    vv_path, vh_path = None, None
    if os.path.isdir(sar_dir):
        for root, _, files in os.walk(sar_dir):
            if "VV_db.tif" in files and "VH_db.tif" in files:
                vv_path = os.path.join(root, "VV_db.tif")
                vh_path = os.path.join(root, "VH_db.tif")
                break

    # 4. Sentinel-2 Optical: NDVI, NDWI, SCL
    optical_dir = os.path.join(media_dir, "satellite", "optical", f"village_{v.id}")
    indices_dir = os.path.join(media_dir, "satellite", "indices", "villages", f"{v.id}")
    s2_raw_dir = os.path.join(media_dir, "satellite", "villages", f"{v.id}")

    ndvi_path, ndwi_path, scl_path = None, None, None

    # Check dedicated optical directory first
    if os.path.isdir(optical_dir):
        for f in os.listdir(optical_dir):
            fl = f.lower()
            if fl in ("ndvi.tif", "ndvi_aligned.tif") and not ndvi_path:
                ndvi_path = os.path.join(optical_dir, f)
            elif fl in ("ndwi.tif", "ndwi_aligned.tif") and not ndwi_path:
                ndwi_path = os.path.join(optical_dir, f)
            elif fl in ("scl.tif", "scl_aligned.tif") and not scl_path:
                scl_path = os.path.join(optical_dir, f)

    # Check indices directory
    if os.path.isdir(indices_dir) and (not ndvi_path or not ndwi_path):
        for root, _, files in os.walk(indices_dir):
            for f in files:
                fl = f.lower()
                if fl in ("ndvi.tif", "ndvi_aligned.tif") and not ndvi_path:
                    ndvi_path = os.path.join(root, f)
                elif fl in ("ndwi.tif", "ndwi_aligned.tif") and not ndwi_path:
                    ndwi_path = os.path.join(root, f)

    # Check raw Sentinel-2 directory for pre-computed files
    if os.path.isdir(s2_raw_dir):
        for root, _, files in os.walk(s2_raw_dir):
            for f in files:
                fl = f.lower()
                if fl in ("scl.tif", "scl_aligned.tif") and not scl_path:
                    scl_path = os.path.join(root, f)
                elif fl in ("ndvi.tif", "ndvi_aligned.tif") and not ndvi_path:
                    ndvi_path = os.path.join(root, f)
                elif fl in ("ndwi.tif", "ndwi_aligned.tif") and not ndwi_path:
                    ndwi_path = os.path.join(root, f)

    # If NDVI/NDWI/SCL are not pre-computed but raw bands exist, derive them automatically
    if (not ndvi_path or not ndwi_path or not scl_path) and os.path.isdir(s2_raw_dir) and os.path.isfile(elev_path):
        derived = derive_and_align_optical_indices(v, s2_raw_dir, elev_path, optical_dir)
        if not ndvi_path: ndvi_path = derived.get("ndvi")
        if not ndwi_path: ndwi_path = derived.get("ndwi")
        if not scl_path: scl_path = derived.get("scl")

    # Verify all 8 files exist
    missing = []
    if not wc_path: missing.append("worldcover_aligned.tif")
    if not os.path.isfile(elev_path): missing.append("elevation_aligned.tif")
    if not os.path.isfile(slope_path): missing.append("slope_aligned.tif")
    if not vv_path: missing.append("VV_db.tif")
    if not vh_path: missing.append("VH_db.tif")
    if not ndvi_path: missing.append("NDVI.tif")
    if not ndwi_path: missing.append("NDWI.tif")
    if not scl_path: missing.append("SCL.tif")

    if missing:
        raise FileNotFoundError(
            f"Missing required rasters for village '{v.name}' (ID: {v.id}): {', '.join(missing)}. "
            f"Please run acquire_sentinel1_sar, acquire_sentinel2_optical, acquire_dem, and acquire_labels first."
        )

    return {
        "worldcover": wc_path,
        "elevation": elev_path,
        "slope": slope_path,
        "vv": vv_path,
        "vh": vh_path,
        "ndvi": ndvi_path,
        "ndwi": ndwi_path,
        "scl": scl_path,
    }


def load_pixel_dataset(village):
    """
    Load aligned multi-modal rasters (SAR + DEM + Optical + SCL + Ground Truth) for a village,
    apply cloud masking (-9999 strategy), flatten to 1D, and clean out background/nodata pixels.

    Returns:
        tuple: (X_clean, y_clean, metadata_dict)
    """
    v = resolve_village_instance(village)
    assets = find_village_raster_assets(v)

    with rasterio.open(assets["vv"]) as f_vv, \
         rasterio.open(assets["vh"]) as f_vh, \
         rasterio.open(assets["elevation"]) as f_el, \
         rasterio.open(assets["slope"]) as f_sl, \
         rasterio.open(assets["ndvi"]) as f_ndvi, \
         rasterio.open(assets["ndwi"]) as f_ndwi, \
         rasterio.open(assets["scl"]) as f_scl, \
         rasterio.open(assets["worldcover"]) as f_wc:

        ref_shape = f_vv.shape
        ref_crs = f_vv.crs
        ref_transform = f_vv.transform

        # 1. SAR & Topography features
        vv_flat = f_vv.read(1).flatten()
        vh_flat = f_vh.read(1).flatten()
        elev_flat = f_el.read(1).flatten()
        slope_flat = f_sl.read(1).flatten()

        # 2. Optical NDVI & NDWI features (resampled to ref grid if needed)
        ndvi_arr = read_and_align_band(f_ndvi, ref_shape, ref_transform, ref_crs, is_categorical=False)
        ndwi_arr = read_and_align_band(f_ndwi, ref_shape, ref_transform, ref_crs, is_categorical=False)
        scl_arr = read_and_align_band(f_scl, ref_shape, ref_transform, ref_crs, is_categorical=True)

        ndvi_flat = ndvi_arr.flatten().astype(np.float32)
        ndwi_flat = ndwi_arr.flatten().astype(np.float32)
        scl_flat = scl_arr.flatten().astype(np.uint8)

        # 3. Ground Truth Labels
        y_flat = f_wc.read(1).flatten()

    # Cloud Masking Strategy (-9999 strategy):
    # SCL values:
    #   0 = No Data, 3 = Cloud Shadows, 8 = Cloud Medium Probability,
    #   9 = Cloud High Probability, 10 = Thin Cirrus
    cloud_indices = np.isin(scl_flat, [0, 3, 8, 9, 10]) | ~np.isfinite(ndvi_flat) | ~np.isfinite(ndwi_flat)
    ndvi_flat[cloud_indices] = -9999.0
    ndwi_flat[cloud_indices] = -9999.0

    clouded_pixels_count = int(np.count_nonzero(cloud_indices))

    # Assemble raw 2D feature matrix [N, 6]
    X_raw = np.column_stack([vv_flat, vh_flat, elev_flat, slope_flat, ndvi_flat, ndwi_flat])

    # Data Cleaning: Filter out background / nodata cells
    # y == 0: outside village boundary
    # -9999.0: raster nodata marker for SAR and DEM (rows with -9999 in NDVI/NDWI are KEPT)
    valid_mask = (
        (y_flat != 0) &
        (elev_flat != -9999.0) &
        (slope_flat != -9999.0) &
        (vv_flat != -9999.0) &
        (vh_flat != -9999.0) &
        ~np.isnan(X_raw).any(axis=1) &
        ~np.isinf(X_raw).any(axis=1)
    )

    X_clean = X_raw[valid_mask].astype(np.float32)
    y_clean = y_flat[valid_mask].astype(np.uint8)

    meta = {
        "village_id": v.id,
        "village_name": v.name,
        "district": getattr(v, "district", "Unknown"),
        "total_raster_cells": int(y_flat.size),
        "valid_labeled_cells": int(len(y_clean)),
        "clouded_cells_flagged": clouded_pixels_count,
        "background_cells": int(np.count_nonzero(y_flat == 0)),
        "raster_shape": ref_shape,
        "crs": ref_crs.to_string() if hasattr(ref_crs, "to_string") else str(ref_crs),
        "transform": ref_transform,
        "assets": assets,
        "feature_names": FEATURE_NAMES,
    }

    return X_clean, y_clean, meta


def train_random_forest_model(
    X,
    y,
    test_size=0.2,
    n_estimators=100,
    max_depth=20,
    random_state=42,
    export_path=None
):
    """
    Train and evaluate a pixel-wise Random Forest classifier on the 6-feature tabular spatial dataset.

    Args:
        X (np.ndarray): Cleaned feature matrix [N_samples, 6].
        y (np.ndarray): Target class labels [N_samples].
        test_size (float): Proportion of dataset held out for evaluation (default: 0.2).
        n_estimators (int): Number of decision trees in forest (default: 100).
        max_depth (int): Maximum depth of each tree (default: 20).
        random_state (int): Seed for reproducibility.
        export_path (str, optional): Target .joblib export path.

    Returns:
        dict: Training evaluation results, classification report, feature importances, and model path.
    """
    base_dir, media_dir = get_base_and_media_dirs()

    # 1. Stratified Train / Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=y
    )

    # 2. Model Initialization & Training
    rf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        n_jobs=-1,
        class_weight="balanced"
    )
    rf.fit(X_train, y_train)

    # 3. Model Evaluation
    y_pred = rf.predict(X_test)
    accuracy = float(accuracy_score(y_test, y_pred))

    # Determine unique classes present in test set for readable report
    unique_labels = sorted(list(np.unique(np.concatenate([y_test, y_pred]))))
    target_names = [f"{LULC_CLASS_NAMES.get(int(cls), f'Class {cls}')} ({cls})" for cls in unique_labels]

    report_str = classification_report(
        y_test,
        y_pred,
        labels=unique_labels,
        target_names=target_names,
        digits=4,
        zero_division=0
    )
    report_dict = classification_report(
        y_test,
        y_pred,
        labels=unique_labels,
        target_names=target_names,
        output_dict=True,
        zero_division=0
    )

    # 4. Feature Importances across all 6 features
    importances = {name: round(float(imp), 4) for name, imp in zip(FEATURE_NAMES, rf.feature_importances_)}
    sorted_importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

    # 5. Export Model Artifact
    if not export_path:
        model_dir = os.path.join(base_dir, "ml", "models")
        os.makedirs(model_dir, exist_ok=True)
        export_path = os.path.join(model_dir, "rf_lulc.joblib")
    else:
        os.makedirs(os.path.dirname(export_path), exist_ok=True)

    # Persist model along with metadata for production inference
    payload = {
        "model": rf,
        "feature_names": FEATURE_NAMES,
        "classes": unique_labels,
        "class_names": LULC_CLASS_NAMES,
        "accuracy": accuracy,
        "feature_importances": sorted_importances,
        "n_samples": int(len(y)),
        "train_samples": int(len(y_train)),
        "test_samples": int(len(y_test)),
        "trained_at": "2026-11-24T17:30:00"
    }
    joblib.dump(payload, export_path)

    # Also save human-readable JSON summary alongside joblib
    meta_json_path = export_path.replace(".joblib", "_metadata.json")
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "accuracy": accuracy,
            "feature_importances": sorted_importances,
            "feature_names": FEATURE_NAMES,
            "n_samples": int(len(y)),
            "train_samples": int(len(y_train)),
            "test_samples": int(len(y_test)),
            "classes_present": {int(c): LULC_CLASS_NAMES.get(int(c), f"Class {c}") for c in unique_labels},
            "classification_report": report_dict,
            "trained_at": "2026-11-24T17:30:00"
        }, f, indent=2)

    return {
        "model": rf,
        "accuracy": accuracy,
        "report_str": report_str,
        "report_dict": report_dict,
        "feature_importances": sorted_importances,
        "export_path": export_path,
        "metadata_path": meta_json_path,
        "n_train": len(y_train),
        "n_test": len(y_test),
    }


def predict_village_lulc_raster(village, model_path=None, output_path=None):
    """
    Perform pixel-wise inference across the entire village raster grid using the
    6-feature stack [VV_db, VH_db, Elevation, Slope, NDVI, NDWI] and export
    the predicted classification GeoTIFF map (rf_predicted_lulc.tif).
    """
    v = resolve_village_instance(village)
    base_dir, media_dir = get_base_and_media_dirs()

    if not model_path:
        model_path = os.path.join(base_dir, "ml", "models", "rf_lulc.joblib")

    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Model file not found at: {model_path}. Train the model first.")

    payload = joblib.load(model_path)
    model = payload["model"]

    # Load multi-modal feature assets
    assets = find_village_raster_assets(v)
    with rasterio.open(assets["vv"]) as f_vv, \
         rasterio.open(assets["vh"]) as f_vh, \
         rasterio.open(assets["elevation"]) as f_el, \
         rasterio.open(assets["slope"]) as f_sl, \
         rasterio.open(assets["ndvi"]) as f_ndvi, \
         rasterio.open(assets["ndwi"]) as f_ndwi, \
         rasterio.open(assets["scl"]) as f_scl, \
         rasterio.open(assets["worldcover"]) as f_wc:

        ref_shape = f_vv.shape
        ref_crs = f_vv.crs
        ref_transform = f_vv.transform
        meta = f_vv.meta.copy()
        h, w = ref_shape

        vv = f_vv.read(1).flatten()
        vh = f_vh.read(1).flatten()
        elev = f_el.read(1).flatten()
        slope = f_sl.read(1).flatten()

        ndvi = read_and_align_band(f_ndvi, ref_shape, ref_transform, ref_crs, is_categorical=False).flatten().astype(np.float32)
        ndwi = read_and_align_band(f_ndwi, ref_shape, ref_transform, ref_crs, is_categorical=False).flatten().astype(np.float32)
        scl = read_and_align_band(f_scl, ref_shape, ref_transform, ref_crs, is_categorical=True).flatten().astype(np.uint8)

        mask_y = f_wc.read(1).flatten()

    # Apply cloud masking (-9999 strategy)
    cloud_mask = np.isin(scl, [0, 3, 8, 9, 10]) | ~np.isfinite(ndvi) | ~np.isfinite(ndwi)
    ndvi[cloud_mask] = -9999.0
    ndwi[cloud_mask] = -9999.0

    X_full = np.column_stack([vv, vh, elev, slope, ndvi, ndwi])
    valid = (
        (mask_y != 0) &
        (elev != -9999.0) &
        (slope != -9999.0) &
        (vv != -9999.0) &
        (vh != -9999.0) &
        ~np.isnan(X_full).any(axis=1) &
        ~np.isinf(X_full).any(axis=1)
    )

    predicted_flat = np.zeros(h * w, dtype=np.uint8)
    if np.any(valid):
        pred_valid = model.predict(X_full[valid])
        predicted_flat[valid] = pred_valid.astype(np.uint8)

    predicted_2d = predicted_flat.reshape((h, w))

    if not output_path:
        out_dir = os.path.join(media_dir, "satellite", "worldcover", f"village_{v.id}")
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, "rf_predicted_lulc.tif")
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    meta.update({
        "driver": "GTiff",
        "dtype": "uint8",
        "nodata": 0,
        "count": 1,
        "compress": "deflate"
    })

    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(predicted_2d, 1)
        dst.update_tags(
            MODEL="RandomForestClassifier",
            VARIABLE="Predicted LULC Classification Map",
            VILLAGE=v.name,
            FEATURES="VV_db, VH_db, Elevation, Slope, NDVI, NDWI",
            TRAINING_DATASET="Sentinel-1 SAR (VV, VH) + Copernicus DEM (Elevation, Slope) + Sentinel-2 Optical (NDVI, NDWI) + ESA WorldCover Ground Truth"
        )

    return output_path


def main():
    """CLI runner when invoked directly via Python."""
    parser = argparse.ArgumentParser(description="Train pixel-wise 6-feature Random Forest for LULC.")
    parser.add_argument("--village", type=str, default="Gahmar", help="Village name or ID (default: 'Gahmar')")
    parser.add_argument("--n-estimators", type=int, default=100, help="Number of trees (default: 100)")
    parser.add_argument("--max-depth", type=int, default=20, help="Max tree depth (default: 20)")
    parser.add_argument("--test-size", type=float, default=0.2, help="Test split ratio (default: 0.2)")
    parser.add_argument("--export-path", type=str, default=None, help="Target path for .joblib")
    parser.add_argument("--predict", action="store_true", help="Generate predicted LULC GeoTIFF")

    args = parser.parse_args()

    print(f"\n[Phase 8] Loading multi-modal spatial dataset for '{args.village}'...")
    X, y, meta = load_pixel_dataset(args.village)

    print(f"  • Total Pixels in Village Bounds: {meta['valid_labeled_cells']:,}")
    print(f"  • Clouded Pixels Masked (-9999):  {meta['clouded_cells_flagged']:,}")
    print(f"  • Feature Stack:                  {meta['feature_names']}")
    print(f"  • Feature Matrix Dimensions:      {X.shape}")

    print(f"\nTraining Random Forest Classifier (n_estimators={args.n_estimators}, max_depth={args.max_depth})...")
    res = train_random_forest_model(
        X,
        y,
        test_size=args.test_size,
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        export_path=args.export_path
    )

    print(f"\n" + "=" * 65)
    print(f"  Overall Validation Accuracy: {res['accuracy'] * 100:.2f}%")
    print("=" * 65)

    print("\nFeature Importances (6-Feature Fusion):")
    for feat, imp in res["feature_importances"].items():
        bar = "█" * int(imp * 40)
        print(f"  {feat:12s} | {imp:.4f} | {bar}")

    print("\nClassification Report:")
    print(res["report_str"])

    print(f"✓ Model exported to:    {res['export_path']}")
    print(f"✓ Metadata exported to: {res['metadata_path']}")

    if args.predict:
        print(f"\nGenerating full-village LULC prediction GeoTIFF...")
        pred_path = predict_village_lulc_raster(args.village, model_path=res["export_path"])
        print(f"✓ Predicted LULC GeoTIFF saved to: {pred_path}")


if __name__ == "__main__":
    main()
