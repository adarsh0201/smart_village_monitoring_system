from django.contrib.gis.db import models
from villages.models import Village


class SatelliteScene(models.Model):
    """
    Metadata record for an acquired Sentinel-2 Level-2A satellite scene
    intersecting a village monitoring area of interest (AOI).
    """
    STATUS_CHOICES = [
        ('discovered', 'Discovered (Metadata Only)'),
        ('downloading', 'Downloading / Processing'),
        ('completed', 'Completed (GeoTIFFs Available)'),
        ('failed', 'Ingestion Failed'),
    ]

    village = models.ForeignKey(
        Village,
        on_delete=models.CASCADE,
        related_name='satellite_scenes',
        help_text="Monitored village unit this satellite scene covers"
    )
    provider = models.CharField(
        max_length=100,
        default='AWS Earth Search / Element 84',
        help_text="STAC catalog data provider"
    )
    collection = models.CharField(
        max_length=100,
        default='sentinel-2-l2a',
        help_text="Satellite imagery collection identifier"
    )
    scene_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Official Sentinel-2 granule/product scene ID"
    )
    acquisition_date = models.DateTimeField(
        db_index=True,
        help_text="Exact timestamp of satellite sensor acquisition (UTC)"
    )
    cloud_cover = models.FloatField(
        help_text="Overall scene cloud coverage percentage (0.0 - 100.0)"
    )
    aoi_cloud_cover = models.FloatField(
        null=True,
        blank=True,
        help_text="Calculated cloud coverage percentage specifically within the village AOI via SCL"
    )
    processing_level = models.CharField(
        max_length=50,
        default='Level-2A',
        help_text="Atmospherically corrected Surface Reflectance (Level-2A)"
    )
    source_url = models.URLField(
        max_length=1000,
        blank=True,
        null=True,
        help_text="Direct STAC item self link or granule URL"
    )
    aoi_geometry = models.PolygonField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Spatial polygon used as the clipping area of interest (EPSG:4326)"
    )
    is_provisional_aoi = models.BooleanField(
        default=True,
        help_text="True if a circular centroid buffer was used instead of an official boundary"
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='discovered',
        db_index=True,
        help_text="Acquisition and clipping status"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if download/clipping failed"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when database record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when database record was last updated"
    )

    class Meta:
        db_table = 'satellite_scenes'
        verbose_name = 'Satellite Scene'
        verbose_name_plural = 'Satellite Scenes'
        ordering = ['-acquisition_date']
        constraints = [
            models.UniqueConstraint(
                fields=['village', 'scene_id'],
                name='unique_village_satellite_scene'
            )
        ]

    def __str__(self):
        return f"{self.scene_id} - {self.village.name} ({self.acquisition_date.strftime('%Y-%m-%d')})"


class SatelliteBand(models.Model):
    """
    Individual spectral band GeoTIFF file clipped to the village monitoring AOI.
    """
    BAND_CHOICES = [
        ('B02', 'B02 - Blue (10m)'),
        ('B03', 'B03 - Green (10m)'),
        ('B04', 'B04 - Red (10m)'),
        ('B08', 'B08 - Near Infrared / NIR (10m)'),
        ('B11', 'B11 - Shortwave Infrared 1 / SWIR 1 (20m)'),
        ('B12', 'B12 - Shortwave Infrared 2 / SWIR 2 (20m)'),
        ('SCL', 'SCL - Scene Classification Layer (20m)'),
    ]

    scene = models.ForeignKey(
        SatelliteScene,
        on_delete=models.CASCADE,
        related_name='bands',
        help_text="Parent satellite scene"
    )
    band_name = models.CharField(
        max_length=20,
        choices=BAND_CHOICES,
        db_index=True,
        help_text="Spectral band identifier"
    )
    file_path = models.CharField(
        max_length=500,
        help_text="Relative storage path inside media directory"
    )
    resolution = models.FloatField(
        help_text="Ground sampling distance / spatial resolution in meters (e.g. 10.0, 20.0)"
    )
    crs = models.CharField(
        max_length=200,
        help_text="Coordinate Reference System (e.g. EPSG:32643 - UTM Zone 43N)"
    )
    width = models.IntegerField(
        null=True,
        blank=True,
        help_text="Raster pixel width"
    )
    height = models.IntegerField(
        null=True,
        blank=True,
        help_text="Raster pixel height"
    )
    file_size = models.BigIntegerField(
        help_text="File size in bytes"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when band was ingested"
    )

    class Meta:
        db_table = 'satellite_bands'
        verbose_name = 'Satellite Band'
        verbose_name_plural = 'Satellite Bands'
        ordering = ['band_name']
        constraints = [
            models.UniqueConstraint(
                fields=['scene', 'band_name'],
                name='unique_scene_band'
            )
        ]

    def __str__(self):
        return f"{self.scene.scene_id} - Band {self.band_name} ({self.resolution}m)"


class SpectralIndex(models.Model):
    """
    Bio-physical and hydrological spectral index raster (NDVI, NDWI, SAVI, MNDWI)
    computed from Sentinel-2 Level-2A surface reflectance bands.
    """
    INDEX_TYPE_CHOICES = [
        ('NDVI', 'NDVI - Normalized Difference Vegetation Index'),
        ('NDWI', 'NDWI - Normalized Difference Water Index (McFeeters)'),
        ('SAVI', 'SAVI - Soil-Adjusted Vegetation Index'),
        ('MNDWI', 'MNDWI - Modified Normalized Difference Water Index (Xu)'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Calculation'),
        ('completed', 'Completed'),
        ('failed', 'Processing Failed'),
    ]

    scene = models.ForeignKey(
        SatelliteScene,
        on_delete=models.CASCADE,
        related_name='indices',
        help_text="Parent satellite scene"
    )
    index_type = models.CharField(
        max_length=20,
        choices=INDEX_TYPE_CHOICES,
        db_index=True,
        help_text="Spectral index type code"
    )
    file_path = models.CharField(
        max_length=500,
        help_text="Relative storage path to generated GeoTIFF"
    )
    png_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Relative storage path to colorized transparent PNG overlay"
    )
    resolution = models.FloatField(
        default=10.0,
        help_text="Ground sampling distance in meters (e.g. 10.0)"
    )
    crs = models.CharField(
        max_length=500,
        help_text="Coordinate Reference System (e.g. EPSG:32643 or WKT)"
    )
    min_value = models.FloatField(
        null=True,
        blank=True,
        help_text="Minimum valid unmasked index value"
    )
    max_value = models.FloatField(
        null=True,
        blank=True,
        help_text="Maximum valid unmasked index value"
    )
    mean = models.FloatField(
        null=True,
        blank=True,
        help_text="Mean valid unmasked index value"
    )
    median = models.FloatField(
        null=True,
        blank=True,
        help_text="Median valid unmasked index value"
    )
    std_dev = models.FloatField(
        null=True,
        blank=True,
        help_text="Standard deviation of valid unmasked index values"
    )
    valid_pixel_count = models.BigIntegerField(
        default=0,
        help_text="Count of unmasked, non-NaN valid data pixels"
    )
    total_pixel_count = models.BigIntegerField(
        default=0,
        help_text="Total number of raster pixels (width * height)"
    )
    cloud_masked = models.BooleanField(
        default=True,
        help_text="True if SCL cloud and shadow mask was applied"
    )
    cloud_pixel_count = models.BigIntegerField(
        default=0,
        help_text="Number of pixels masked out as cloud or shadow"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        help_text="Calculation and generation status"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if calculation failed"
    )
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Formula coefficients (e.g. {'L': 0.5})"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when index calculation record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when index was last updated"
    )

    class Meta:
        db_table = 'satellite_spectral_indices'
        verbose_name = 'Spectral Index'
        verbose_name_plural = 'Spectral Indices'
        ordering = ['scene', 'index_type']
        constraints = [
            models.UniqueConstraint(
                fields=['scene', 'index_type'],
                name='unique_scene_index_type'
            )
        ]

    def __str__(self):
        return f"{self.scene.scene_id} - {self.index_type} ({self.status})"

