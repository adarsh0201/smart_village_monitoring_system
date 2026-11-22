from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from villages.models import Village
from .models import SatelliteScene, SpectralIndex
from .serializers import SatelliteSceneSerializer, SpectralIndexSerializer
from .services.search import search_sentinel2_scenes
from .services.ingestion import ingest_sentinel2_scene
from .services.indices import compute_scene_indices


class SatelliteSceneListView(generics.ListAPIView):
    """
    GET /api/satellite/scenes/
    List all ingested satellite scenes. Optional query param: ?village_id=<id>
    """
    serializer_class = SatelliteSceneSerializer

    def get_queryset(self):
        queryset = SatelliteScene.objects.all().prefetch_related('bands').select_related('village')
        village_id = self.request.query_params.get('village_id')
        if village_id:
            queryset = queryset.filter(village_id=village_id)
        return queryset.order_by('-acquisition_date')


class SatelliteSceneDetailView(generics.RetrieveAPIView):
    """
    GET /api/satellite/scenes/<id>/
    Retrieve metadata, spatial resolution, and band download links for a specific scene.
    """
    queryset = SatelliteScene.objects.all().prefetch_related('bands').select_related('village')
    serializer_class = SatelliteSceneSerializer
    lookup_field = 'pk'


class VillageSatelliteScenesView(generics.ListAPIView):
    """
    GET /api/villages/<village_id>/satellite-scenes/
    List all acquired satellite scenes for a specific village.
    """
    serializer_class = SatelliteSceneSerializer

    def get_queryset(self):
        village_id = self.kwargs.get('village_id')
        return SatelliteScene.objects.filter(village_id=village_id).prefetch_related('bands').select_related('village').order_by('-acquisition_date')


class SatelliteSearchView(APIView):
    """
    POST /api/satellite/search/
    Query real Sentinel-2 Level-2A STAC catalog for a village monitoring AOI.
    
    Payload:
    {
      "village_id": 1,
      "start_date": "2024-01-01",     # Optional (default: 60 days before end_date)
      "end_date": "2024-04-01",       # Optional (default: today)
      "max_cloud_cover": 20.0,        # Optional (default: 20%)
      "buffer_km": 2.5                # Optional (default: 2.5 km provisional buffer)
    }
    """
    def post(self, request, *args, **kwargs):
        village_id = request.data.get('village_id')
        if not village_id:
            return Response(
                {"error": "Field 'village_id' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        village = get_object_or_404(Village, pk=village_id)
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        max_cloud_cover = request.data.get('max_cloud_cover', 20.0)
        buffer_km = request.data.get('buffer_km', 2.5)

        try:
            results = search_sentinel2_scenes(
                village=village,
                start_date=start_date,
                end_date=end_date,
                max_cloud_cover=max_cloud_cover,
                limit=15,
                buffer_km=buffer_km
            )
            return Response(results, status=status.HTTP_200_OK)
        except Exception as exc:
            return Response(
                {"error": f"Satellite search failed: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SatelliteDownloadView(APIView):
    """
    POST /api/satellite/download/
    Window-clip and ingest Sentinel-2 spectral bands for the village monitoring AOI.
    
    Payload:
    {
      "village_id": 1,
      "scene_id": "S2B_43RCH_20240322_0_L2A",
      "buffer_km": 2.5,               # Optional (default: 2.5 km)
      "force_refresh": false          # Optional
    }
    """
    def post(self, request, *args, **kwargs):
        village_id = request.data.get('village_id')
        scene_id = request.data.get('scene_id')

        if not village_id or not scene_id:
            return Response(
                {"error": "Both 'village_id' and 'scene_id' are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        village = get_object_or_404(Village, pk=village_id)
        buffer_km = request.data.get('buffer_km', 2.5)
        force_refresh = request.data.get('force_refresh', False)

        try:
            res = ingest_sentinel2_scene(
                village=village,
                scene_id=scene_id,
                buffer_km=buffer_km,
                force_refresh=force_refresh
            )
            serializer = SatelliteSceneSerializer(res["scene"], context={'request': request})
            return Response({
                "message": res["message"],
                "cached": res.get("cached", False),
                "scene": serializer.data,
            }, status=status.HTTP_201_CREATED if not res.get("cached") else status.HTTP_200_OK)
        except Exception as exc:
            return Response(
                {"error": f"Satellite ingestion failed: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SceneIndicesListView(generics.ListAPIView):
    """
    GET /api/satellite/scenes/<pk>/indices/
    List all computed spectral indices for a specific satellite scene.
    """
    serializer_class = SpectralIndexSerializer

    def get_queryset(self):
        scene_id = self.kwargs.get('pk')
        scene = get_object_or_404(SatelliteScene, pk=scene_id)
        return SpectralIndex.objects.filter(scene=scene).order_by('index_type')


class ComputeSceneIndicesView(APIView):
    """
    POST /api/satellite/scenes/<pk>/compute-indices/
    Compute all four spectral indices (NDVI, NDWI, SAVI, MNDWI) for a Sentinel-2 scene.
    
    Optional JSON payload:
    {
      "mask_clouds": true,     # Default: true
      "overwrite": false       # Default: false (idempotent; returns existing if already computed)
    }
    """
    def post(self, request, pk, *args, **kwargs):
        scene = get_object_or_404(SatelliteScene, pk=pk)
        mask_clouds = request.data.get('mask_clouds', True)
        overwrite = request.data.get('overwrite', False)

        try:
            result = compute_scene_indices(scene, mask_clouds=mask_clouds, overwrite=overwrite)
            indices = SpectralIndex.objects.filter(scene=scene).order_by('index_type')
            serializer = SpectralIndexSerializer(indices, many=True, context={'request': request})
            return Response({
                "success": True,
                "message": result.get("message", f"Indices computed for scene {scene.scene_id}."),
                "scene_id": scene.scene_id,
                "village_id": scene.village_id,
                "village_name": scene.village.name,
                "cached": result.get("cached", False),
                "indices": serializer.data,
            }, status=status.HTTP_200_OK)
        except Exception as exc:
            return Response(
                {"error": f"Index computation failed: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

