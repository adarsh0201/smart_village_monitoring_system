import json
from django.db import connection
from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon


def generate_village_monitoring_aoi(village, buffer_km=2.5):
    """
    Generate the spatial Area of Interest (AOI) polygon for a village.
    
    If the village has an official administrative boundary polygon/multipolygon,
    that boundary is returned directly.
    
    If no administrative boundary exists (boundary is None), this generates a
    configurable geodesic circular buffer around the village centroid using PostGIS.
    This is explicitly labeled as a 'Provisional Monitoring AOI', NOT an official boundary.
    
    Returns a dict with:
      - geometry: GEOSGeometry Polygon in EPSG:4326
      - geojson: GeoJSON dict
      - bbox: [minx, miny, maxx, maxy] in EPSG:4326
      - is_provisional: bool
      - buffer_km: float or None
      - description: str
    """
    buffer_km = float(buffer_km) if buffer_km else 2.5

    # 1. Official boundary if present
    if village.boundary:
        # If MultiPolygon, get convex hull or bounding polygon if single poly
        geom = village.boundary
        minx, miny, maxx, maxy = geom.extent
        return {
            'geometry': geom,
            'geojson': json.loads(geom.geojson),
            'bbox': [minx, miny, maxx, maxy],
            'is_provisional': False,
            'buffer_km': None,
            'description': f"Official administrative boundary polygon for {village.name}",
        }

    # 2. Provisional circular geodesic buffer via PostGIS ST_Buffer on geography
    lng = village.location.x
    lat = village.location.y
    buffer_meters = buffer_km * 1000.0

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ST_AsGeoJSON(
                ST_Buffer(
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 
                    %s
                )::geometry
            );
        """, [lng, lat, buffer_meters])
        geojson_str = cursor.fetchone()[0]

    geom = GEOSGeometry(geojson_str, srid=4326)
    geojson_dict = json.loads(geojson_str)
    minx, miny, maxx, maxy = geom.extent

    return {
        'geometry': geom,
        'geojson': geojson_dict,
        'bbox': [minx, miny, maxx, maxy],
        'is_provisional': True,
        'buffer_km': buffer_km,
        'description': (
            f"Provisional monitoring AOI ({buffer_km:.1f} km circular buffer "
            f"around centroid of {village.name} at [{lng:.4f}, {lat:.4f}])"
        ),
    }

