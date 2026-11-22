"""
Django Management Command: sync_village_centroids

Synchronizes village point locations (markers) with their official boundary centroids.

Solves the spatial offset between the village location marker pin and the
village administrative boundary polygon on the GIS map.
"""

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from villages.models import Village


class Command(BaseCommand):
    help = "Synchronize village marker coordinates (village.location) with boundary centroids"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate without committing changes to PostgreSQL"
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write("=" * 75)
        self.stdout.write("SYNCHRONIZING VILLAGE MARKER POINTERS WITH BOUNDARY CENTROIDS")
        self.stdout.write("=" * 75)

        villages = Village.objects.all()
        updated_count = 0

        for v in villages:
            if not v.boundary:
                self.stdout.write(self.style.WARNING(f"[-] {v.name}: No boundary geometry defined. Skipping."))
                continue

            old_lon = v.location.x if v.location else None
            old_lat = v.location.y if v.location else None

            # Calculate centroid of official boundary polygon
            centroid = v.boundary.centroid
            new_lon = round(centroid.x, 6)
            new_lat = round(centroid.y, 6)

            # Compute offset in km
            offset_km = 0.0
            if old_lon and old_lat:
                import math
                r = 6371.0
                p1, p2 = math.radians(old_lat), math.radians(new_lat)
                dp = math.radians(new_lat - old_lat)
                dl = math.radians(new_lon - old_lon)
                a = math.sin(dp / 2)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2)**2
                offset_km = r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

            v.location = Point(new_lon, new_lat, srid=4326)

            if not dry_run:
                v.save(update_fields=["location", "updated_at"])

            self.stdout.write(self.style.SUCCESS(
                f"✓ {v.name:<12} ({v.district}):\n"
                f"    Old Pointer: [{old_lon:.5f}, {old_lat:.5f}]\n"
                f"    New Pointer: [{new_lon:.5f}, {new_lat:.5f}] (Boundary Centroid)\n"
                f"    Offset Corrected: {offset_km:.2f} km -> 0.00 km (Perfect Alignment)"
            ))
            updated_count += 1

        self.stdout.write("=" * 75)
        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY RUN] No changes committed to PostgreSQL."))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Successfully aligned all {updated_count} village pointer markers with their boundary centroids!"
            ))
        self.stdout.write("=" * 75)
