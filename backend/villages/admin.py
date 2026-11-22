from django.contrib.gis import admin
from .models import Village


@admin.register(Village)
class VillageAdmin(admin.GISModelAdmin):
    list_display = ('name', 'district', 'state', 'area_hectares', 'population', 'created_at')
    search_fields = ('name', 'district')
    list_filter = ('district', 'state')
