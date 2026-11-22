"""
Raster Clipping Service: Precision Boundary Masking using Rasterio and GeoDjango.

Provides production-ready functions to clip multi-spectral and derived
Sentinel-2 GeoTIFF rasters to the exact administrative MultiPolygon borders
of a Village, preserving all spatial metadata, CRS, affine transforms,
data types, and band layers.
"""

import os
import json
import logging
import rasterio
from rasterio.mask import mask
import shapely.geometry
import shapely.ops
from pyproj import Transformer

from django.conf import settings

logger = logging.getLogger("satellite.clipping")

# Path to rasterio PROJ database to prevent Windows GDAL DLL conflicts
RASTERIO_PROJ_DIR = os.path.join(os.path.dirname(rasterio.__file__), "proj_data")


class MissingBoundaryError(ValueError):
    """Raised when a village does not possess an official or defined boundary MultiPolygon."""
    pass


def transform_geojson_geometry(geom_geojson_dict, source_crs, target_crs):
    """
    Reproject a GeoJSON geometry dictionary from source_crs to target_crs.
    
    Args:
        geom_geojson_dict (dict): GeoJSON geometry dictionary.
        source_crs (str/CRS): Source Coordinate Reference System (e.g. 'EPSG:4326').
        target_crs (str/CRS): Target Coordinate Reference System (e.g. 'EPSG:32643').
        
    Returns:
        shapely.geometry.base.BaseGeometry: Transformed Shapely geometry.
    """
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    shape_obj = shapely.geometry.shape(geom_geojson_dict)
    return shapely.ops.transform(transformer.transform, shape_obj)


def clip_geotiff_to_village(
    input_raster_path,
    output_raster_path,
    village,
    nodata=None,
    crop=True,
    all_touched=False,
    compression="deflate"
):
    """
    Clip a GeoTIFF raster to the exact MultiPolygon boundary of a Village.
    
    Preserves:
      - All bands (single-band or multi-band)
      - Native pixel data type (e.g. uint16, float32)
      - Coordinate Reference System (CRS)
      - Source metadata tags
      - Affine transform (re-aligned to clipped window)
      
    Args:
        input_raster_path (str): Path to input source GeoTIFF (relative or absolute).
        output_raster_path (str): Destination path for clipped GeoTIFF.
        village (Village): GeoDjango Village model instance with a valid MultiPolygon boundary.
        nodata (float/int, optional): Explicit NoData value. Defaults to source raster's nodata.
        crop (bool): Whether to crop raster bounding extent to polygon bounds (default: True).
        all_touched (bool): If True, all pixels touched by the boundary polygon will be updated.
        compression (str): GeoTIFF compression codec (default: 'deflate').
        
    Returns:
        dict: Summary of clipping results including dimensions, file sizes, and metadata.
        
    Raises:
        MissingBoundaryError: If village has no boundary geometry.
        FileNotFoundError: If input raster does not exist.
        ValueError: If geometry is invalid or does not intersect the raster footprint.
    """
    # 1. Validate village boundary geometry
    if not village:
        raise ValueError("A valid Village model instance must be provided.")

    if not village.boundary:
        raise MissingBoundaryError(
            f"Village '{village.name}' (ID: {village.id}) does not have an "
            f"administrative boundary MultiPolygon defined in the database. "
            f"Please update the village boundary via 'python manage.py update_village_boundaries' first."
        )

    # Resolve paths relative to MEDIA_ROOT if needed
    if not os.path.isabs(input_raster_path):
        input_raster_path = os.path.join(settings.MEDIA_ROOT, input_raster_path)
    if not os.path.isabs(output_raster_path):
        output_raster_path = os.path.join(settings.MEDIA_ROOT, output_raster_path)

    if not os.path.exists(input_raster_path):
        raise FileNotFoundError(f"Input raster not found at: {input_raster_path}")

    os.makedirs(os.path.dirname(output_raster_path), exist_ok=True)

    # 2. Open source raster and prepare reprojected boundary
    with rasterio.Env(PROJ_LIB=RASTERIO_PROJ_DIR, PROJ_DATA=RASTERIO_PROJ_DIR):
        with rasterio.open(input_raster_path) as src:
            src_crs = src.crs
            src_meta = src.meta.copy()
            src_tags = src.tags()
            src_nodata = src.nodata

            # Determine NoData value
            out_nodata = nodata if nodata is not None else src_nodata
            if out_nodata is None:
                out_nodata = -9999.0 if "float" in src.dtypes[0] else 0

            # 3. Transform village boundary (EPSG:4326) to raster native CRS
            boundary_geojson = json.loads(village.boundary.geojson)
            try:
                geom_transformed = transform_geojson_geometry(
                    boundary_geojson,
                    source_crs="EPSG:4326",
                    target_crs=src_crs
                )
            except Exception as exc:
                raise ValueError(
                    f"Failed to reproject boundary of '{village.name}' to raster CRS ({src_crs}): {exc}"
                )

            # 4. Perform mask clipping
            try:
                out_image, out_transform = mask(
                    dataset=src,
                    shapes=[geom_transformed],
                    crop=crop,
                    nodata=out_nodata,
                    all_touched=all_touched
                )
            except ValueError as exc:
                raise ValueError(
                    f"Raster clipping failed for '{village.name}': {exc}. "
                    f"Ensure the village boundary intersects the raster spatial extent."
                )

            # 5. Build output metadata preserving all bands & attributes
            out_meta = src_meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform,
                "nodata": out_nodata,
                "compress": compression,
            })

            # 6. Write masked GeoTIFF
            with rasterio.open(output_raster_path, "w", **out_meta) as dst:
                dst.write(out_image)
                if src_tags:
                    dst.update_tags(**src_tags)
                dst.update_tags(
                    CLIPPED_BY="SmartVillageMonitor",
                    VILLAGE_NAME=village.name,
                    VILLAGE_DISTRICT=village.district,
                    BOUNDARY_SOURCE="Official Administrative Boundary"
                )

    file_size_bytes = os.path.getsize(output_raster_path)
    logger.info(
        f"Successfully clipped '{os.path.basename(input_raster_path)}' to {village.name} border: "
        f"shape=({out_image.shape[1]}, {out_image.shape[2]}), size={file_size_bytes/1024:.1f} KB"
    )

    return {
        "success": True,
        "village_name": village.name,
        "input_raster": input_raster_path,
        "output_raster": output_raster_path,
        "dimensions": (out_image.shape[1], out_image.shape[2]),
        "band_count": out_image.shape[0],
        "dtype": str(out_image.dtype),
        "crs": str(src_crs),
        "nodata": out_nodata,
        "file_size_bytes": file_size_bytes,
    }


def clip_scene_to_village_boundary(scene, output_directory=None, overwrite=False):
    """
    Clip all spectral bands of an acquired SatelliteScene to its village's exact boundary.
    
    Args:
        scene (SatelliteScene): SatelliteScene model instance.
        output_directory (str, optional): Destination root directory.
        overwrite (bool): Whether to re-clip existing outputs.
        
    Returns:
        dict: Summary of all clipped bands.
    """
    village = scene.village
    if not village.boundary:
        raise MissingBoundaryError(
            f"Cannot clip scene '{scene.scene_id}': Village '{village.name}' has no boundary geometry."
        )

    if not output_directory:
        output_directory = os.path.join(
            settings.MEDIA_ROOT,
            "satellite",
            "villages_clipped",
            str(village.id),
            scene.scene_id
        )

    os.makedirs(output_directory, exist_ok=True)
    clipped_bands = []

    for band in scene.bands.all():
        input_band_path = os.path.join(settings.MEDIA_ROOT, band.file_path)
        dest_filename = f"{band.band_name}.tif"
        output_band_path = os.path.join(output_directory, dest_filename)

        if os.path.exists(output_band_path) and not overwrite:
            clipped_bands.append({
                "band_name": band.band_name,
                "output_path": output_band_path,
                "cached": True
            })
            continue

        res = clip_geotiff_to_village(
            input_raster_path=input_band_path,
            output_raster_path=output_band_path,
            village=village
        )
        clipped_bands.append(res)

    return {
        "scene_id": scene.scene_id,
        "village": village.name,
        "clipped_bands_count": len(clipped_bands),
        "output_directory": output_directory,
        "bands": clipped_bands
    }
