"""
Sentinel-1 SAR Search Service: STAC Discovery & Asset Signing for Radar Imagery.

Queries Microsoft Planetary Computer and AWS Earth Search STAC APIs for
Sentinel-1 C-band SAR Ground Range Detected (GRD) scenes in IW (Interferometric Wide Swath)
mode intersecting official village administrative MultiPolygon boundaries.

Features:
- Precision spatial filtering using official village MultiPolygon geometries (STAC 'intersects' or 'bbox').
- Cloud-penetrating all-weather radar discovery (day/night, unaffected by monsoon clouds or dust).
- Dual polarization filtering (VV: soil moisture/water; VH: vegetation/biomass structure).
- Orbit direction selection (ASCENDING / DESCENDING).
- Automatic on-the-fly SAS token signing for direct GeoTIFF downloading from Microsoft Planetary Computer.
"""

import datetime
import logging
import requests
from django.utils import timezone
from satellite.services.aoi import generate_village_monitoring_aoi

logger = logging.getLogger("satellite.sar")

PLANETARY_COMPUTER_STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PLANETARY_COMPUTER_SAS_URL = "https://planetarycomputer.microsoft.com/api/sas/v1/token"
EARTH_SEARCH_STAC_URL = "https://earth-search.aws.element84.com/v1/search"


def get_planetary_computer_sas_token(collection="sentinel-1-grd"):
    """
    Fetch a temporary Shared Access Signature (SAS) token from Microsoft
    Planetary Computer for authenticated blob asset downloads.
    """
    try:
        url = f"{PLANETARY_COMPUTER_SAS_URL}/{collection}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json().get("token")
    except Exception as exc:
        logger.warning(f"Could not retrieve Planetary Computer SAS token: {exc}")
    return None


def sign_asset_url(url, sas_token):
    """
    Append SAS token to an Azure blob storage asset URL.
    """
    if not url:
        return None
    if not sas_token:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{sas_token}"


def search_sentinel1_sar_scenes(
    village,
    start_date=None,
    end_date=None,
    orbit_direction=None,  # 'ascending', 'descending', or None for both
    limit=10,
    buffer_km=2.5,
    collection="sentinel-1-grd",
    sign_urls=True
):
    """
    Search Sentinel-1 C-band SAR imagery for a village AOI via STAC API.

    Args:
        village (Village): Village model instance with official boundary.
        start_date (str/datetime, optional): Start of search window (defaults to 60 days ago).
        end_date (str/datetime, optional): End of search window (defaults to now).
        orbit_direction (str, optional): 'ascending' or 'descending'.
        limit (int): Maximum scenes to return (default 10).
        buffer_km (float): Bounding buffer fallback if village lacks boundary.
        collection (str): STAC collection ('sentinel-1-grd' or 'sentinel-1-rtc').
        sign_urls (bool): Whether to sign Azure asset URLs with SAS tokens for direct downloading.

    Returns:
        list[dict]: Structured SAR scene metadata records ready for ingestion.
    """
    # 1. Extract AOI geometry and bounding box from Village
    aoi_data = generate_village_monitoring_aoi(village, buffer_km=buffer_km)
    bbox = aoi_data["bbox"]  # [minx, miny, maxx, maxy]
    has_official_boundary = not aoi_data.get("is_provisional", True)

    # 2. Date range formatting
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

    # 3. Construct STAC Query Filters
    query_filters = {
        "sar:instrument_mode": {"eq": "IW"}  # Interferometric Wide Swath (standard 10m resolution)
    }

    if orbit_direction and orbit_direction.lower() in ["ascending", "descending"]:
        query_filters["sat:orbit_state"] = {"eq": orbit_direction.lower()}

    # Construct request payload with intersects or bbox
    payload = {
        "collections": [collection],
        "bbox": bbox,
        "datetime": datetime_str,
        "query": query_filters,
        "limit": min(limit, 25),
        "sortby": [{"field": "properties.datetime", "direction": "desc"}]
    }

    # If official boundary GeoJSON geometry is available, use exact intersects geometry
    if has_official_boundary and "geojson" in aoi_data:
        payload["intersects"] = aoi_data["geojson"]
        # When 'intersects' is provided in STAC API, 'bbox' is omitted to avoid conflict
        del payload["bbox"]

    logger.info(
        f"Querying Sentinel-1 SAR STAC for '{village.name}': "
        f"datetime={datetime_str}, orbit={orbit_direction or 'any'}, "
        f"boundary={'Official MultiPolygon' if has_official_boundary else 'Centroid Buffer'}"
    )

    headers = {"Content-Type": "application/json"}
    provider_name = "Microsoft Planetary Computer"
    sas_token = None

    try:
        response = requests.post(PLANETARY_COMPUTER_STAC_URL, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        if sign_urls:
            sas_token = get_planetary_computer_sas_token(collection)
    except requests.RequestException as exc:
        logger.warning(f"Planetary Computer query failed ({exc}), attempting AWS Earth Search STAC fallback...")
        try:
            # Fallback to AWS STAC using standard bbox payload
            payload["bbox"] = bbox
            payload.pop("intersects", None)
            response = requests.post(EARTH_SEARCH_STAC_URL, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            provider_name = "AWS Earth Search"
        except requests.RequestException as err:
            logger.error(f"SAR STAC query failed across all providers: {err}")
            return []

    features = data.get("features", [])
    results = []

    for item in features:
        props = item.get("properties", {})
        assets = item.get("assets", {})
        item_id = item.get("id")

        # Extract polarization asset links (VV and VH)
        vv_asset = assets.get("vv") or assets.get("VV")
        vh_asset = assets.get("vh") or assets.get("VH")
        preview_asset = assets.get("rendered_preview") or assets.get("thumbnail")

        vv_raw_url = vv_asset.get("href") if vv_asset else None
        vh_raw_url = vh_asset.get("href") if vh_asset else None
        preview_raw_url = preview_asset.get("href") if preview_asset else None

        # Sign URLs if token obtained
        vv_url = sign_asset_url(vv_raw_url, sas_token)
        vh_url = sign_asset_url(vh_raw_url, sas_token)
        preview_url = sign_asset_url(preview_raw_url, sas_token)

        results.append({
            "scene_id": item_id,
            "satellite": "Sentinel-1",
            "platform": props.get("platform", "Sentinel-1"),
            "acquisition_date": props.get("datetime"),
            "orbit_state": props.get("sat:orbit_state", "unknown"),
            "relative_orbit": props.get("sat:relative_orbit"),
            "slice_number": props.get("sar:slice_number"),
            "instrument_mode": props.get("sar:instrument_mode", "IW"),
            "polarizations": props.get("sar:polarizations", ["VV", "VH"]),
            "resolution_meters": 10.0,
            "cloud_penetrating": True,
            "village_id": village.id,
            "village_name": village.name,
            "has_official_boundary": has_official_boundary,
            "assets": {
                "vv": vv_url,
                "vh": vh_url,
                "preview": preview_url,
            },
            "source_provider": provider_name,
            "is_signed": bool(sas_token)
        })

    logger.info(f"Discovered {len(results)} Sentinel-1 SAR scene(s) for '{village.name}'.")
    return results
