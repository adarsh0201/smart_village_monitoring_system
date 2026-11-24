from django.urls import path
from . import views
from satellite.views import VillageSatelliteScenesView

urlpatterns = [
    path('', views.home, name='api-home'),
    path('villages/', views.VillageListCreateView.as_view(), name='village-list-create'),
    path('villages/<int:pk>/', views.VillageDetailView.as_view(), name='village-detail'),
    path('villages/<int:village_id>/satellite-scenes/', VillageSatelliteScenesView.as_view(), name='village-satellite-scenes'),
    path('villages/<int:pk>/predicted-map/', views.VillagePredictedMapView.as_view(), name='village-predicted-map'),
    path('villages/<int:pk>/analytics/', views.VillageLulcAnalyticsView.as_view(), name='village-lulc-analytics'),
]
