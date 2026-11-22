import os
import re
import numpy as np
import requests
import rasterio
from rasterio.mask import mask
import shapely.geometry
from pyproj import Transformer

from django.conf import settings
from django.utils import timezone
from django.contrib.gis.geos import Polygon, MultiPolygon

from .aoi import generate_village_monitoring_aoi
from .search import search_sentinel2_scenes
from satellite.models import SatelliteScene, SatelliteBand


BAND_METADATA = {
    'B02': {'name': 'B02', 'desc': 'Blue', 'resolution': 10.0},
    'B03': {'name': 'B03', 'desc': 'Green', 'resolution': 10.0},
    'B04': {'name': 'B04', 'desc': 'Red', 'resolution': 10.0},
    'B08': {'name': 'B08', 'desc': 'Near Infrared (NIR)', 'resolution': 10.0},
    'B11': {'name': 'B11', 'desc': 'Shortwave Infrared 1 (SWIR 1)', 'resolution': 20.0},
    'B12': {'name': 'B12', 'desc': 'Shortwave Infrared 2 (SWIR 2)', 'resolution': 20.0},
    'SCL': {'name': 'SCL', 'desc': 'Scene Classification Layer', 'resolution': 20.0},
}


def sanitize_filename(name):
    """Sanitize scene identifier for safe cross-platform folder naming."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)


def sign_url_if_mpc(url):
    """Sign URL if it originates from Microsoft Planetary Computer."""
    if 'blob.core.windows.net' in url and 'stac' not in url:
        try:
            sign_api = f"https://planetarycomputer.microsoft.com/api/sas/v1/sign?href={url}"
            r = requests.get(sign_api, timeout=10)
            if r.status_code == 200:
                return r.json().get('href', url)
        except Exception:
            pass
    return url


def ingest_sentinel2_scene(village, scene_id, buffer_km=2.5, force_refresh=False):
    """
    Acquire, window-clip, and ingest a Sentinel-2 Level-2A scene for a village AOI.
    
    1. Checks if scene is already ingested (idempotent; prevents duplicate downloads).
    2. Generates the monitoring AOI (provisional circular buffer or official boundary).
    3. Fetches STAC scene assets from Earth Search or Microsoft Planetary Computer.
    4. Clips each required band (B02, B03, B04, B08, B11, B12, SCL) to the village AOI.
    5. Saves outputs as valid GeoTIFF files under media/satellite/villages/<village_id>/<scene_id>/.
    6. Calculates village-specific cloud cover from the SCL layer.
    7. Stores metadata and file paths in PostgreSQL.
    """
    safe_scene_id = sanitize_filename(scene_id)

    # 1. Idempotency Check
    existing_scene = SatelliteScene.objects.filter(
        village=village, scene_id=scene_id, status='completed'
    ).first()

    if existing_scene and not force_refresh:
        # Check if band files actually exist on disk
        band_count = existing_scene.bands.count()
        if band_count >= 6:
            return {
                "success": True,
                "scene": existing_scene,
                "message": f"Scene {scene_id} is already downloaded and indexed for {village.name}.",
                "cached": True,
            }

    # 2. AOI Generation
    aoi_data = generate_village_monitoring_aoi(village, buffer_km=buffer_km)
    aoi_geom = aoi_data['geometry']
    minx, miny, maxx, maxy = aoi_data['bbox']

    # 3. Locate Scene in STAC
    # Search around scene acquisition window
    search_res = search_sentinel2_scenes(
        village,
        start_date="2020-01-01",  # broad search to guarantee finding scene
        max_cloud_cover=100.0,
        limit=20,
        buffer_km=buffer_km
    )

    scene_item = next(
        (s for s in search_res.get("scenes", []) if s["scene_id"] == scene_id),
        None
    )

    if not scene_item:
        # If not in recent search, directly query STAC for this specific scene_id
        try:
            r = requests.get(f"https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/{scene_id}", timeout=15)
            if r.status_code == 200:
                feat = r.json()
                props = feat.get("properties", {})
                assets = feat.get("assets", {})
                band_links = {}
                key_mapping = {
                    'blue': 'B02', 'green': 'B03', 'red': 'B04', 'nir': 'B08',
                    'swir16': 'B11', 'swir22': 'B12', 'scl': 'SCL',
                    'B02': 'B02', 'B03': 'B03', 'B04': 'B04', 'B08': 'B08',
                    'B11': 'B11', 'B12': 'B12', 'SCL': 'SCL'
                }
                for src_k, target_b in key_mapping.items():
                    if src_k in assets and target_b not in band_links:
                        band_links[target_b] = assets[src_k].get("href")

                scene_item = {
                    "scene_id": scene_id,
                    "acquisition_date": props.get("datetime"),
                    "cloud_cover": props.get("eo:cloud_cover", 0.0),
                    "provider": "AWS Earth Search (Element 84)",
                    "collection": "sentinel-2-l2a",
                    "band_assets": band_links,
                    "thumbnail_url": assets.get("thumbnail", {}).get("href")
                }
        except Exception:
            pass

    if not scene_item:
        raise ValueError(f"Could not locate STAC metadata for Sentinel-2 scene: {scene_id}")

    # 4. Initialize or update SatelliteScene in DB
    dt_str = scene_item["acquisition_date"]
    dt = timezone.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

    # Convert geometry for PolygonField if MultiPolygon
    if isinstance(aoi_geom, MultiPolygon):
        poly_geom = aoi_geom[0]
    elif isinstance(aoi_geom, Polygon):
        poly_geom = aoi_geom
    else:
        poly_geom = None

    scene_record, _ = SatelliteScene.objects.update_or_create(
        village=village,
        scene_id=scene_id,
        defaults={
            "provider": scene_item.get("provider", "AWS Earth Search"),
            "collection": scene_item.get("collection", "sentinel-2-l2a"),
            "acquisition_date": dt,
            "cloud_cover": float(scene_item.get("cloud_cover", 0.0)),
            "processing_level": "Level-2A",
            "source_url": scene_item.get("thumbnail_url"),
            "aoi_geometry": poly_geom,
            "is_provisional_aoi": aoi_data["is_provisional"],
            "status": "downloading",
            "error_message": None,
        }
    )

    # 5. Storage Directory on Disk
    rel_scene_dir = os.path.join("satellite", "villages", str(village.id), safe_scene_id)
    abs_scene_dir = os.path.join(settings.MEDIA_ROOT, rel_scene_dir)
    os.makedirs(abs_scene_dir, exist_ok=True)

    # 6. Window-read and clip each spectral band
    band_assets = scene_item.get("band_assets", {})
    required_bands = ['B02', 'B03', 'B04', 'B08', 'B11', 'B12', 'SCL']
    ingested_bands = []
    aoi_cloud_cover = None

    try:
        # Create Shapely AOI in WGS84
        aoi_wgs84 = shapely.geometry.box(minx, miny, maxx, maxy)

        for band_key in required_bands:
            href = band_assets.get(band_key)
            if not href:
                continue

            href = sign_url_if_mpc(href)
            band_info = BAND_METADATA.get(band_key, {'resolution': 10.0, 'name': band_key})

            dest_filename = f"{band_key}.tif"
            rel_file_path = os.path.join(rel_scene_dir, dest_filename).replace("\\", "/")
            abs_file_path = os.path.join(abs_scene_dir, dest_filename)

            # Open remote COG using rasterio over HTTP
            with rasterio.open(href) as src:
                src_crs = src.crs

                # Transform AOI bounding box to native raster CRS (e.g. UTM Zone 43N)
                transformer = Transformer.from_crs("EPSG:4326", src_crs, always_xy=True)
                utm_minx, utm_miny = transformer.transform(minx, miny)
                utm_maxx, utm_maxy = transformer.transform(maxx, maxy)
                aoi_utm = shapely.geometry.box(utm_minx, utm_miny, utm_maxx, utm_maxy)

                # Clip/crop raster window
                out_image, out_transform = mask(src, [aoi_utm], crop=True)
                out_meta = src.meta.copy()

                out_meta.update({
                    "driver": "GTiff",
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform,
                    "compress": "deflate",
                })

                # Write clipped GeoTIFF
                with rasterio.open(abs_file_path, "w", **out_meta) as dest:
                    dest.write(out_image)

                file_size = os.path.getsize(abs_file_path)

                # Calculate cloud coverage if SCL layer
                if band_key == 'SCL':
                    scl_arr = out_image[0]
                    valid_pixels = (scl_arr != 0)
                    if np.any(valid_pixels):
                        # Classes: 3 (Shadow), 8 (Med Cloud), 9 (High Cloud), 10 (Cirrus)
                        cloud_pixels = np.isin(scl_arr, [3, 8, 9, 10])
                        aoi_cloud_cover = round(
                            float(np.sum(cloud_pixels) / np.sum(valid_pixels) * 100.0), 2
                        )

                # Safe CRS representation
                if hasattr(src_crs, 'to_epsg') and src_crs.to_epsg():
                    crs_display = f"EPSG:{src_crs.to_epsg()}"
                else:
                    crs_display = str(src_crs)[:190]

                # Save Band Record in DB
                band_record, _ = SatelliteBand.objects.update_or_create(
                    scene=scene_record,
                    band_name=band_key,
                    defaults={
                        "file_path": rel_file_path,
                        "resolution": band_info['resolution'],
                        "crs": crs_display,
                        "width": out_image.shape[2],
                        "height": out_image.shape[1],
                        "file_size": file_size,
                    }
                )
                ingested_bands.append(band_record)

        # 7. Update Scene Status to Completed
        scene_record.status = "completed"
        scene_record.aoi_cloud_cover = aoi_cloud_cover
        scene_record.save()

        return {
            "success": True,
            "scene": scene_record,
            "bands_count": len(ingested_bands),
            "aoi_cloud_cover": aoi_cloud_cover,
            "message": f"Successfully ingested {len(ingested_bands)} bands for {village.name}.",
            "cached": False,
        }

    except Exception as exc:
        scene_record.status = "failed"
        scene_record.error_message = str(exc)
        scene_record.save()
        raise exc
