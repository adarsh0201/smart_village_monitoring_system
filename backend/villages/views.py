from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Village
from .serializers import VillageSerializer


@api_view(["GET"])
def home(request):
    """
    Backend service status and system health probe for React frontend dashboard.
    """
    village_count = Village.objects.count()
    return Response({
        "project": "Satellite Data-Based Smart Village Monitoring System",
        "backend": "Django REST Framework",
        "database": "PostgreSQL 18 + PostGIS 3.6",
        "status": "Running",
        "monitored_villages_count": village_count,
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
