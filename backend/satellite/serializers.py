from rest_framework import serializers
from django.conf import settings
from .models import SatelliteScene, SatelliteBand, SpectralIndex


class SatelliteBandSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    file_size_formatted = serializers.SerializerMethodField()

    class Meta:
        model = SatelliteBand
        fields = [
            'id',
            'band_name',
            'file_path',
            'download_url',
            'resolution',
            'crs',
            'width',
            'height',
            'file_size',
            'file_size_formatted',
            'created_at',
        ]

    def get_download_url(self, obj):
        request = self.context.get('request')
        url = settings.MEDIA_URL + obj.file_path.lstrip('/')
        if request:
            return request.build_absolute_uri(url)
        return f"http://127.0.0.1:8000/{url.lstrip('/')}"

    def get_file_size_formatted(self, obj):
        if not obj.file_size:
            return "0 B"
        size_kb = obj.file_size / 1024.0
        if size_kb > 1024.0:
            return f"{size_kb / 1024.0:.2f} MB"
        return f"{size_kb:.1f} KB"


class SpectralIndexSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    png_url = serializers.SerializerMethodField()

    class Meta:
        model = SpectralIndex
        fields = [
            'id',
            'scene',
            'index_type',
            'file_path',
            'download_url',
            'png_path',
            'png_url',
            'resolution',
            'crs',
            'min_value',
            'max_value',
            'mean',
            'median',
            'std_dev',
            'valid_pixel_count',
            'total_pixel_count',
            'cloud_masked',
            'cloud_pixel_count',
            'status',
            'error_message',
            'parameters',
            'created_at',
            'updated_at',
        ]

    def get_download_url(self, obj):
        request = self.context.get('request')
        url = settings.MEDIA_URL + obj.file_path.lstrip('/')
        if request:
            return request.build_absolute_uri(url)
        return f"http://127.0.0.1:8000/{url.lstrip('/')}"

    def get_png_url(self, obj):
        if not obj.png_path:
            return None
        request = self.context.get('request')
        url = settings.MEDIA_URL + obj.png_path.lstrip('/')
        if request:
            return request.build_absolute_uri(url)
        return f"http://127.0.0.1:8000/{url.lstrip('/')}"


class SatelliteSceneSerializer(serializers.ModelSerializer):
    village_name = serializers.CharField(source='village.name', read_only=True)
    district = serializers.CharField(source='village.district', read_only=True)
    bands = SatelliteBandSerializer(many=True, read_only=True)
    bands_count = serializers.IntegerField(source='bands.count', read_only=True)
    indices = SpectralIndexSerializer(many=True, read_only=True)
    indices_count = serializers.IntegerField(source='indices.count', read_only=True)

    class Meta:
        model = SatelliteScene
        fields = [
            'id',
            'village',
            'village_name',
            'district',
            'provider',
            'collection',
            'scene_id',
            'acquisition_date',
            'cloud_cover',
            'aoi_cloud_cover',
            'processing_level',
            'source_url',
            'is_provisional_aoi',
            'status',
            'error_message',
            'bands_count',
            'bands',
            'indices_count',
            'indices',
            'created_at',
            'updated_at',
        ]

