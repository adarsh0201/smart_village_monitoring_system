"""
Pixel-Wise Random Forest Classifier for Land Use / Land Cover (LULC).

Integrates multi-sensor feature rasters and ground truth masks:
1. Feature Layers:
   - Sentinel-1 SAR Dual-Pol Backscatter (VV_db.tif, VH_db.tif in dB)
   - Copernicus DEM 30m Elevation (elevation_aligned.tif in meters)
   - Topographic Slope (slope_aligned.tif in degrees)
2. Ground Truth Target Mask:
   - ESA WorldCover 10m Ground Truth (worldcover_aligned.tif)
3. Preprocessing:
   - Spatial unrolling / flattening to tabular matrix: X in R^{N x 4}, y in R^{N}
   - Data cleaning: Filters out nodata cells (y == 0, background, or invalid values)
4. Training & Validation:
   - Stratified Train / Test split (80/20)
   - Multi-class Random Forest with class-weight balancing
5. Model Persistence:
   - Saves trained model to backend/ml/models/rf_lulc.joblib
"""

import os
import re
import json
import logging
import joblib
import numpy as np
import rasterio

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

from django.conf import settings
from django.utils import timezone
from villages.models import Village

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

FEATURE_NAMES = ["VV_db", "VH_db", "Elevation", "Slope"]


def resolve_village_instance(village_ref):
    """Resolve a Village model instance from an instance, integer PK, or name string."""
    if isinstance(village_ref, Village):
        return village_ref
    if isinstance(village_ref, int) or (isinstance(village_ref, str) and str(village_ref).isdigit()):
        return Village.objects.get(pk=int(village_ref))
    if isinstance(village_ref, str):
        v = Village.objects.filter(name__iexact=village_ref.strip()).first()
        if v:
            return v
    raise ValueError(f"Could not resolve village from identifier: {village_ref}")


def find_village_raster_assets(village):
    """
    Locate the required aligned feature rasters and ground truth mask for a village:
    - worldcover_aligned.tif
    - elevation_aligned.tif
    - slope_aligned.tif
    - VV_db.tif & VH_db.tif
    """
    v = resolve_village_instance(village)

    # 1. WorldCover Target Mask
    wc_candidates = [
        os.path.join(settings.MEDIA_ROOT, "satellite", "worldcover", f"village_{v.id}", "worldcover_aligned.tif"),
        os.path.join(settings.MEDIA_ROOT, "satellite", "dem", f"village_{v.id}", "worldcover_aligned.tif"),
    ]
    wc_path = next((p for p in wc_candidates if os.path.isfile(p)), None)

    # 2. Topography: Elevation & Slope
    dem_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "dem", f"village_{v.id}")
    elev_path = os.path.join(dem_dir, "elevation_aligned.tif")
    slope_path = os.path.join(dem_dir, "slope_aligned.tif")

    # 3. Sentinel-1 SAR: VV & VH
    sar_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "sar", f"village_{v.id}")
    vv_path, vh_path = None, None
    if os.path.isdir(sar_dir):
        for root, _, files in os.walk(sar_dir):
            if "VV_db.tif" in files and "VH_db.tif" in files:
                vv_path = os.path.join(root, "VV_db.tif")
                vh_path = os.path.join(root, "VH_db.tif")
                break

    # Verify all 5 files exist
    missing = []
    if not wc_path: missing.append("worldcover_aligned.tif")
    if not os.path.isfile(elev_path): missing.append("elevation_aligned.tif")
    if not os.path.isfile(slope_path): missing.append("slope_aligned.tif")
    if not vv_path: missing.append("VV_db.tif")
    if not vh_path: missing.append("VH_db.tif")

    if missing:
        raise FileNotFoundError(
            f"Missing required rasters for village '{v.name}' (ID: {v.id}): {', '.join(missing)}. "
            f"Please run acquire_sentinel1_sar, acquire_dem, and acquire_labels first."
        )

    return {
        "worldcover": wc_path,
        "elevation": elev_path,
        "slope": slope_path,
        "vv": vv_path,
        "vh": vh_path,
    }


def load_pixel_dataset(village):
    """
    Load aligned rasters for a village, flatten them to 1D, and clean out background/nodata pixels.

    Returns:
        tuple: (X_clean, y_clean, metadata_dict)
    """
    v = resolve_village_instance(village)
    assets = find_village_raster_assets(v)

    with rasterio.open(assets["vv"]) as f_vv, \
         rasterio.open(assets["vh"]) as f_vh, \
         rasterio.open(assets["elevation"]) as f_el, \
         rasterio.open(assets["slope"]) as f_sl, \
         rasterio.open(assets["worldcover"]) as f_wc:

        # Verify spatial shape compatibility
        if not (f_vv.shape == f_vh.shape == f_el.shape == f_sl.shape == f_wc.shape):
            raise ValueError(
                f"Raster shape mismatch for '{v.name}': "
                f"SAR={f_vv.shape}, Elev={f_el.shape}, Slope={f_sl.shape}, WorldCover={f_wc.shape}"
            )

        raster_shape = f_vv.shape
        raster_crs = f_vv.crs.to_string()
        raster_transform = f_vv.transform

        vv_flat = f_vv.read(1).flatten()
        vh_flat = f_vh.read(1).flatten()
        elev_flat = f_el.read(1).flatten()
        slope_flat = f_sl.read(1).flatten()
        y_flat = f_wc.read(1).flatten()

    # Assemble raw 2D feature matrix [N, 4]
    X_raw = np.column_stack([vv_flat, vh_flat, elev_flat, slope_flat])

    # Data Cleaning: Filter out background / nodata cells
    # y == 0: outside village boundary
    # -9999.0: raster nodata marker
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
        "district": v.district,
        "total_raster_cells": int(y_flat.size),
        "valid_labeled_cells": int(len(y_clean)),
        "background_cells": int(np.count_nonzero(y_flat == 0)),
        "raster_shape": raster_shape,
        "crs": raster_crs,
        "transform": raster_transform,
        "assets": assets,
        "feature_names": FEATURE_NAMES,
    }

    return X_clean, y_clean, meta


def train_random_forest_model(
    X,
    y,
    test_size=0.2,
    n_estimators=100,
    max_depth=16,
    random_state=42,
    export_path=None
):
    """
    Train and evaluate a pixel-wise Random Forest classifier on tabular spatial data.

    Args:
        X (np.ndarray): Cleaned feature matrix [N_samples, N_features].
        y (np.ndarray): Target class labels [N_samples].
        test_size (float): Proportion of dataset to hold out for evaluation (default: 0.2).
        n_estimators (int): Number of decision trees in forest (default: 100).
        max_depth (int): Maximum depth of each tree (default: 16).
        random_state (int): Seed for reproducibility.
        export_path (str, optional): Target .joblib export path.

    Returns:
        dict: Training evaluation results, classification report, feature importances, and model path.
    """
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

    # 4. Feature Importances
    importances = {name: round(float(imp), 4) for name, imp in zip(FEATURE_NAMES, rf.feature_importances_)}
    sorted_importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

    # 5. Export Model Artifact
    if not export_path:
        model_dir = os.path.join(settings.BASE_DIR, "ml", "models")
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
        "trained_at": timezone.now().isoformat()
    }
    joblib.dump(payload, export_path)

    # Also save human-readable JSON summary alongside joblib
    meta_json_path = export_path.replace(".joblib", "_metadata.json")
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump({
            "accuracy": accuracy,
            "feature_importances": sorted_importances,
            "n_samples": int(len(y)),
            "train_samples": int(len(y_train)),
            "test_samples": int(len(y_test)),
            "classes_present": {int(c): LULC_CLASS_NAMES.get(int(c), f"Class {c}") for c in unique_labels},
            "classification_report": report_dict,
            "trained_at": timezone.now().isoformat()
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
    Perform pixel-wise inference across the entire village raster grid and export
    the predicted classification GeoTIFF map (rf_predicted_lulc.tif).
    """
    v = resolve_village_instance(village)
    if not model_path:
        model_path = os.path.join(settings.BASE_DIR, "ml", "models", "rf_lulc.joblib")

    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"Model file not found at: {model_path}. Train the model first.")

    payload = joblib.load(model_path)
    model = payload["model"]

    # Load raw feature assets
    assets = find_village_raster_assets(v)
    with rasterio.open(assets["vv"]) as f_vv, \
         rasterio.open(assets["vh"]) as f_vh, \
         rasterio.open(assets["elevation"]) as f_el, \
         rasterio.open(assets["slope"]) as f_sl, \
         rasterio.open(assets["worldcover"]) as f_wc:

        meta = f_vv.meta.copy()
        h, w = f_vv.shape

        vv = f_vv.read(1).flatten()
        vh = f_vh.read(1).flatten()
        elev = f_el.read(1).flatten()
        slope = f_sl.read(1).flatten()
        mask_y = f_wc.read(1).flatten()

    X_full = np.column_stack([vv, vh, elev, slope])
    valid = (mask_y != 0) & (elev != -9999.0) & (slope != -9999.0) & (vv != -9999.0) & ~np.isnan(X_full).any(axis=1)

    predicted_flat = np.zeros(h * w, dtype=np.uint8)
    if np.any(valid):
        pred_valid = model.predict(X_full[valid])
        predicted_flat[valid] = pred_valid.astype(np.uint8)

    predicted_2d = predicted_flat.reshape((h, w))

    if not output_path:
        out_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "worldcover", f"village_{v.id}")
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, "rf_predicted_lulc.tif")

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
            TRAINING_DATASET="Sentinel-1 SAR (VV, VH) + Copernicus DEM (Elevation, Slope) + ESA WorldCover Ground Truth"
        )

    return output_path
