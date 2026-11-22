from django.urls import path
from . import views

urlpatterns = [
    path('scenes/', views.SatelliteSceneListView.as_view(), name='satellite-scene-list'),
    path('scenes/<int:pk>/', views.SatelliteSceneDetailView.as_view(), name='satellite-scene-detail'),
    path('scenes/<int:pk>/indices/', views.SceneIndicesListView.as_view(), name='scene-indices-list'),
    path('scenes/<int:pk>/compute-indices/', views.ComputeSceneIndicesView.as_view(), name='scene-compute-indices'),
    path('search/', views.SatelliteSearchView.as_view(), name='satellite-search'),
    path('download/', views.SatelliteDownloadView.as_view(), name='satellite-download'),
    path('villages/<int:village_id>/satellite-scenes/', views.VillageSatelliteScenesView.as_view(), name='village-satellite-scenes'),
]

