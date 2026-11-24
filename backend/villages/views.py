import io
import os
import logging
import numpy as np
import rasterio
import pyproj
from PIL import Image

from django.conf import settings
from django.http import HttpResponse, Http404
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Village
from .serializers import VillageSerializer

# Ensure rasterio internal PROJ data directory takes precedence
RASTERIO_PROJ_DATA = os.path.join(os.path.dirname(rasterio.__file__), "proj_data")
if os.path.isdir(RASTERIO_PROJ_DATA):
    os.environ["PROJ_LIB"] = RASTERIO_PROJ_DATA
    os.environ["PROJ_DATA"] = RASTERIO_PROJ_DATA

logger = logging.getLogger(__name__)

# Standard ESA WorldCover & RF LULC Class Color Mapping (RGBA)
LULC_COLOR_PALETTE = {
    0: (0, 0, 0, 0),            # Nodata / background -> 100% Transparent
    10: (27, 94, 32, 230),      # Tree cover -> Dark Green
    20: (255, 187, 34, 230),    # Shrubland -> Orange-Yellow
    30: (255, 235, 59, 230),    # Grassland -> Yellow
    40: (76, 175, 80, 230),     # Cropland -> Green
    50: (244, 67, 54, 230),     # Built-up -> Red
    60: (158, 158, 158, 230),   # Bare / sparse -> Grey
    70: (240, 240, 240, 230),   # Snow/ice -> White
    80: (33, 150, 243, 230),    # Permanent water bodies -> Blue
    90: (0, 150, 160, 230),     # Herbaceous wetland -> Teal
    95: (0, 200, 120, 230),     # Mangroves -> Emerald
    100: (180, 220, 140, 230),  # Moss/lichen -> Light Moss
}

# Metadata descriptions & Hex colors for Analytics UI
LULC_CLASSES_META = {
    10: {"name": "Tree Cover", "color": "#1b5e20", "description": "Continuous and dense tree canopy"},
    20: {"name": "Shrubland", "color": "#ffb300", "description": "Low woody vegetation & shrubs"},
    30: {"name": "Grassland", "color": "#ffeb3b", "description": "Natural grasslands & pastures"},
    40: {"name": "Cropland", "color": "#4caf50", "description": "Agricultural fields & crops"},
    50: {"name": "Built-up", "color": "#f44336", "description": "Buildings, roads & settlements"},
    60: {"name": "Bare / Sparse", "color": "#9e9e9e", "description": "Exposed soil, sand & rocks"},
    70: {"name": "Snow & Ice", "color": "#f5f5f5", "description": "Permanent snow or ice"},
    80: {"name": "Permanent Water", "color": "#2196f3", "description": "Rivers, ponds & lakes"},
    90: {"name": "Wetland", "color": "#009688", "description": "Herbaceous wetland"},
    95: {"name": "Mangroves", "color": "#00c878", "description": "Coastal mangrove vegetation"},
    100: {"name": "Moss & Lichen", "color": "#b4dc8c", "description": "Moss & lichen surfaces"},
}


def get_village_lulc_raster_path(village_id):
    """Locate the predicted LULC GeoTIFF or ground truth fallback for a village."""
    candidates = [
        os.path.join(settings.MEDIA_ROOT, "satellite", "worldcover", f"village_{village_id}", "rf_predicted_lulc.tif"),
        os.path.join(settings.MEDIA_ROOT, "satellite", "worldcover", f"village_{village_id}", "worldcover_aligned.tif"),
        os.path.join(settings.MEDIA_ROOT, "satellite", "dem", f"village_{village_id}", "worldcover_aligned.tif"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


@api_view(["GET"])
def home(request):
    """
    Backend service status and system health probe for React frontend dashboard.
    """
    village_count = 0
    try:
        village_count = Village.objects.count()
    except Exception:
        pass

    return Response({
        "project": "Satellite Data-Based Smart Village Monitoring System",
        "backend": "Django REST Framework",
        "database": "PostgreSQL 18 + PostGIS 3.6",
        "status": "Running",
        "monitored_villages_count": village_count,
        "phase": "Phase 8: Multi-Modal Optical Feature Fusion (SAR + DEM + S2 Optical)",
    })


class VillageListCreateView(generics.ListCreateAPIView):
    """
    API view to list all villages or create a new village record.
    GET  /api/villages/  -> List all villages
    POST /api/villages/  -> Create a new village record
    """
    queryset = Village.objects.all().order_by('name')
    serializer_class = VillageSerializer


class VillageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view to retrieve, update, or delete a village instance.
    GET    /api/villages/<id>/ -> Retrieve village record
    PUT    /api/villages/<id>/ -> Full update
    PATCH  /api/villages/<id>/ -> Partial update
    DELETE /api/villages/<id>/ -> Delete village record
    """
    queryset = Village.objects.all()
    serializer_class = VillageSerializer
    lookup_field = 'pk'


class VillagePredictedMapView(APIView):
    """
    Colorized Map Serving Endpoint:
    GET /api/villages/<id>/predicted-map/

    Reads rf_predicted_lulc.tif (or worldcover_aligned.tif), applies a custom
    discrete colormap (40=Green, 50=Red, 80=Blue, 10=Dark Green, 0=Transparent),
    and streams a transparent PNG suitable for Leaflet ImageOverlay.
    """

    def get(self, request, pk=None, village_id=None):
        target_id = pk or village_id
        raster_path = get_village_lulc_raster_path(target_id)

        if not raster_path:
            raise Http404(f"No LULC raster found for village ID {target_id}.")

        try:
            with rasterio.open(raster_path) as src:
                data = src.read(1)

            h, w = data.shape
            rgba = np.zeros((h, w, 4), dtype=np.uint8)

            # Apply custom colormap to integer classes
            for class_val, color in LULC_COLOR_PALETTE.items():
                mask = (data == class_val)
                rgba[mask] = color

            # Optional opacity override via query param ?opacity=0.85
            opacity_param = request.query_params.get("opacity")
            if opacity_param is not None:
                try:
                    opacity_val = float(opacity_param)
                    if 0.0 <= opacity_val <= 1.0:
                        non_transparent = (rgba[..., 3] > 0)
                        rgba[..., 3][non_transparent] = int(255 * opacity_val)
                except ValueError:
                    pass

            img = Image.fromarray(rgba, 'RGBA')
            buffer = io.BytesIO()
            img.save(buffer, format='PNG', optimize=True)
            png_bytes = buffer.getvalue()

            response = HttpResponse(png_bytes, content_type='image/png')
            response['Cache-Control'] = 'public, max-age=3600'
            response['Content-Length'] = str(len(png_bytes))
            return response

        except Exception as exc:
            logger.exception(f"Failed to generate predicted map PNG for village {target_id}: {exc}")
            return HttpResponse(f"Error rendering map: {exc}", status=500, content_type="text/plain")


class VillageLulcAnalyticsView(APIView):
    """
    LULC Analytics Endpoint:
    GET /api/villages/<id>/analytics/

    Counts pixels in rf_predicted_lulc.tif, multiplies by 100 sq meters (10m x 10m grid),
    computes area in hectares for each class, calculates geographic bounding box in WGS 84
    for Leaflet ImageOverlay positioning, and returns comprehensive JSON statistics.
    """

    def get(self, request, pk=None, village_id=None):
        target_id = pk or village_id

        # Resolve village name
        village_name = f"Village {target_id}"
        village_district = "Unknown"
        village_state = "India"
        try:
            v = Village.objects.filter(pk=int(target_id)).first()
            if v:
                village_name = v.name
                village_district = v.district
                village_state = v.state
        except Exception:
            pass

        raster_path = get_village_lulc_raster_path(target_id)
        if not raster_path:
            return Response({
                "village_id": int(target_id),
                "village_name": village_name,
                "district": village_district,
                "state": village_state,
                "available": False,
                "message": f"AI LULC prediction has not yet been computed for {village_name}.",
                "breakdown": []
            }, status=200)

        try:
            with rasterio.open(raster_path) as src:
                arr = src.read(1)
                crs = src.crs
                bounds = src.bounds
                tags = src.tags()

            # Calculate WGS 84 bounds for Leaflet ImageOverlay: [[south, west], [north, east]]
            if crs.to_string() == "EPSG:4326":
                leaflet_bounds = [
                    [round(bounds.bottom, 6), round(bounds.left, 6)],
                    [round(bounds.top, 6), round(bounds.right, 6)],
                ]
            else:
                transformer = pyproj.Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
                west, south = transformer.transform(bounds.left, bounds.bottom)
                east, north = transformer.transform(bounds.right, bounds.top)
                leaflet_bounds = [
                    [round(south, 6), round(west, 6)],
                    [round(north, 6), round(east, 6)],
                ]

            total_grid_pixels = int(arr.size)
            unique_classes, counts = np.unique(arr, return_counts=True)
            class_counts = dict(zip(unique_classes, counts))

            # 0 represents nodata / outside official boundary
            background_pixels = int(class_counts.get(0, 0))
            valid_pixels = total_grid_pixels - background_pixels

            # 1 pixel = 10m x 10m = 100 m^2 = 0.01 hectares
            total_area_hectares = round(valid_pixels * 0.01, 2)

            breakdown = []
            for cls_val in sorted(class_counts.keys()):
                cls_int = int(cls_val)
                if cls_int == 0:
                    continue  # Exclude background nodata from landcover distribution

                pixel_cnt = int(class_counts[cls_val])
                hectares = round(pixel_cnt * 0.01, 2)
                pct = round((pixel_cnt / valid_pixels * 100.0), 2) if valid_pixels > 0 else 0.0

                meta = LULC_CLASSES_META.get(cls_int, {
                    "name": f"Class {cls_int}",
                    "color": "#607d8b",
                    "description": "Unclassified Land Cover"
                })

                breakdown.append({
                    "class_id": cls_int,
                    "name": meta["name"],
                    "pixels": pixel_cnt,
                    "hectares": hectares,
                    "percentage": pct,
                    "color": meta["color"],
                    "description": meta["description"],
                })

            # Sort breakdown by area descending
            breakdown.sort(key=lambda x: x["hectares"], reverse=True)

            is_rf_model = "rf_predicted_lulc.tif" in os.path.basename(raster_path)

            return Response({
                "village_id": int(target_id),
                "village_name": village_name,
                "district": village_district,
                "state": village_state,
                "available": True,
                "total_area_hectares": total_area_hectares,
                "valid_pixels": valid_pixels,
                "total_grid_pixels": total_grid_pixels,
                "bounds": leaflet_bounds,
                "predicted_map_url": f"/api/villages/{target_id}/predicted-map/",
                "model_type": tags.get("MODEL", "RandomForestClassifier (Phase 8 Optical Fusion)" if is_rf_model else "ESA WorldCover 10m Ground Truth"),
                "features": tags.get("FEATURES", "VV_db, VH_db, Elevation, Slope, NDVI, NDWI"),
                "raster_file": os.path.basename(raster_path),
                "breakdown": breakdown,
            })

        except Exception as exc:
            logger.exception(f"Error computing LULC analytics for village {target_id}: {exc}")
            return Response({"error": f"Failed to compute analytics: {exc}"}, status=500)
