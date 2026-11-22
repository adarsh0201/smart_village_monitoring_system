from django.contrib import admin
from .models import SatelliteScene, SatelliteBand


class SatelliteBandInline(admin.TabularInline):
    model = SatelliteBand
    extra = 0
    readonly_fields = ('band_name', 'resolution', 'crs', 'width', 'height', 'file_size', 'file_path')


@admin.register(SatelliteScene)
class SatelliteSceneAdmin(admin.ModelAdmin):
    list_display = ('scene_id', 'village', 'acquisition_date', 'cloud_cover', 'aoi_cloud_cover', 'status', 'created_at')
    list_filter = ('status', 'provider', 'collection', 'village__district')
    search_fields = ('scene_id', 'village__name', 'village__district')
    inlines = [SatelliteBandInline]


@admin.register(SatelliteBand)
class SatelliteBandAdmin(admin.ModelAdmin):
    list_display = ('band_name', 'scene', 'resolution', 'crs', 'width', 'height', 'file_size')
    list_filter = ('band_name', 'crs')
    search_fields = ('band_name', 'scene__scene_id')
