from django.contrib.gis.db import models
from django.core.validators import MinValueValidator


class Village(models.Model):
    """
    Spatial data model for rural ground monitoring units (villages)
    in Rajasthan, integrated with satellite observation and GIS datasets.
    """
    name = models.CharField(
        max_length=150,
        db_index=True,
        help_text="Official or recognized village name"
    )
    district = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Administrative district within Rajasthan"
    )
    state = models.CharField(
        max_length=100,
        default='Rajasthan',
        help_text="State name (default: Rajasthan)"
    )
    location = models.PointField(
        srid=4326,
        help_text="Representative geographic coordinates (EPSG:4326 Point: Longitude, Latitude)"
    )
    boundary = models.MultiPolygonField(
        srid=4326,
        blank=True,
        null=True,
        help_text="Administrative boundary multipolygon (EPSG:4326)"
    )
    area_hectares = models.FloatField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0.0)],
        help_text="Total land area in hectares"
    )
    population = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Latest official census or estimated population"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when record was last updated"
    )

    class Meta:
        db_table = 'villages'
        verbose_name = 'Village'
        verbose_name_plural = 'Villages'
        ordering = ['name']
        indexes = [
            models.Index(fields=['district', 'name'], name='idx_village_dist_name'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'district', 'state'],
                name='unique_village_district_state'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.district}, {self.state})"

    @property
    def latitude(self):
        return self.location.y if self.location else None

    @property
    def longitude(self):
        return self.location.x if self.location else None
