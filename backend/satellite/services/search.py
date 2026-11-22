import datetime
import requests
from django.utils import timezone
from .aoi import generate_village_monitoring_aoi
from satellite.models import SatelliteScene


EARTH_SEARCH_STAC_URL = "https://earth-search.aws.element84.com/v1/search"
PLANETARY_COMPUTER_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"


def search_sentinel2_scenes(
    village,
    start_date=None,
    end_date=None,
    max_cloud_cover=20,
    limit=10,
    buffer_km=2.5,
    collection="sentinel-2-l2a"
):
    """
    Search real Sentinel-2 Level-2A imagery for a village monitoring AOI via STAC API.
    
    Returns structured list of available scenes with acquisition dates,
    scene IDs, cloud cover %, download status, and provider metadata.
    """
    # 1. Generate Village AOI
    aoi_data = generate_village_monitoring_aoi(village, buffer_km=buffer_km)
    bbox = aoi_data['bbox']  # [minx, miny, maxx, maxy]

    # 2. Date range formatting (defaults to previous 60 days if omitted)
    now = timezone.now()
    if not end_date:
        end_dt = now
    elif isinstance(end_date, str):
        end_dt = datetime.datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    else:
        end_dt = end_date

    if not start_date:
        start_dt = end_dt - datetime.timedelta(days=60)
    elif isinstance(start_date, str):
        start_dt = datetime.datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    else:
        start_dt = start_date

    datetime_str = f"{start_dt.strftime('%Y-%m-%dT00:00:00Z')}/{end_dt.strftime('%Y-%m-%dT23:59:59Z')}"
    max_cloud_cover = float(max_cloud_cover) if max_cloud_cover is not None else 20.0

    # 3. Query Earth Search STAC
    headers = {"Content-Type": "application/json"}
    payload = {
        "collections": [collection],
        "bbox": bbox,
        "datetime": datetime_str,
        "query": {
            "eo:cloud_cover": {"lte": max_cloud_cover}
        },
        "limit": min(limit, 20),
        "sortby": [{"field": "properties.datetime", "direction": "desc"}]
    }

    features = []
    provider = "AWS Earth Search (Element 84)"

    try:
        resp = requests.post(EARTH_SEARCH_STAC_URL, json=payload, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            features = data.get("features", [])
        else:
            # Fallback to Planetary Computer
            provider = "Microsoft Planetary Computer"
            resp_mpc = requests.post(PLANETARY_COMPUTER_STAC_URL, json=payload, headers=headers, timeout=20)
            if resp_mpc.status_code == 200:
                features = resp_mpc.json().get("features", [])
    except Exception as exc:
        # Fallback to Planetary Computer if Earth Search times out
        try:
            provider = "Microsoft Planetary Computer"
            resp_mpc = requests.post(PLANETARY_COMPUTER_STAC_URL, json=payload, headers=headers, timeout=20)
            if resp_mpc.status_code == 200:
                features = resp_mpc.json().get("features", [])
        except Exception:
            features = []

    # 4. Parse features into unified Sentinel-2 scene records
    downloaded_scenes = set(
        SatelliteScene.objects.filter(village=village, status='completed')
        .values_list('scene_id', flat=True)
    )

    results = []
    for feat in features:
        props = feat.get("properties", {})
        scene_id = feat.get("id")
        dt_str = props.get("datetime")
        cloud_pct = props.get("eo:cloud_cover", 0.0)

        # Map band assets
        assets = feat.get("assets", {})
        band_links = {}

        # Standard Earth Search band keys
        key_mapping = {
            'blue': 'B02',
            'green': 'B03',
            'red': 'B04',
            'nir': 'B08',
            'swir16': 'B11',
            'swir22': 'B12',
            'scl': 'SCL',
            # MPC direct names
            'B02': 'B02',
            'B03': 'B03',
            'B04': 'B04',
            'B08': 'B08',
            'B11': 'B11',
            'B12': 'B12',
            'SCL': 'SCL',
        }

        for src_key, target_band in key_mapping.items():
            if src_key in assets and target_band not in band_links:
                band_links[target_band] = assets[src_key].get("href")

        # Thumbnail if available
        thumbnail_url = (
            assets.get("thumbnail", {}).get("href")
            or assets.get("visual", {}).get("href")
            or assets.get("rendered_preview", {}).get("href")
        )

        results.append({
            "scene_id": scene_id,
            "acquisition_date": dt_str,
            "cloud_cover": round(float(cloud_pct), 2),
            "provider": provider,
            "collection": collection,
            "processing_level": "Level-2A",
            "tile_id": props.get("grid:code") or props.get("s2:mgrs_tile", "43RCH"),
            "thumbnail_url": thumbnail_url,
            "band_assets": band_links,
            "required_bands_available": all(
                b in band_links for b in ['B02', 'B03', 'B04', 'B08', 'B11', 'B12', 'SCL']
            ),
            "is_downloaded": scene_id in downloaded_scenes,
        })

    return {
        "village": {
            "id": village.id,
            "name": village.name,
            "district": village.district,
            "state": village.state,
        },
        "aoi": {
            "type": "provisional" if aoi_data["is_provisional"] else "official",
            "buffer_km": aoi_data["buffer_km"],
            "bbox": bbox,
            "description": aoi_data["description"],
        },
        "query": {
            "start_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": end_dt.strftime("%Y-%m-%d"),
            "max_cloud_cover": max_cloud_cover,
            "collection": collection,
        },
        "total_scenes_found": len(results),
        "scenes": results,
    }

