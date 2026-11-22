"""
Django Management Command: fallback_geometries

Generates and saves standard synthetic polygonal monitoring boundaries
(1.5 km - 2.5 km radius polygonal buffers / octagons) for target villages
(specifically Bhadla and Kuldhara) in PostgreSQL/PostGIS.

Features:
- Precision projection via local UTM (EPSG:32642 for Western Rajasthan).
- Clean 16-sided or 8-sided regular polygonal geometry in WGS84 (EPSG:4326).
- Guaranteed centering on verified village coordinates (village.location).
- Updates Village.boundary (MultiPolygon) and calculates exact metric area in hectares.
- Automatically synchronizes data/boundaries/rajasthan_pilot_villages.geojson.
"""

import os
import json
import math
import pyproj
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon as GeosPolygon
from django.db import transaction
from villages.models import Village

# Default configurations for fallback geometries
TARGET_FALLBACK_CONFIGS = {
    "bhadla": {
        "name": "Bhadla",
        "radius_km": 1.5,
        "num_sides": 16,  # 16-gon buffer
        "utm_epsg": 32642,
        "description": "Standard synthetic 1.5 km monitoring buffer for Bhadla"
    },
    "kuldhara": {
        "name": "Kuldhara",
        "radius_km": 1.5,
        "num_sides": 16,  # 16-gon buffer
        "utm_epsg": 32642,
        "description": "Standard synthetic 1.5 km monitoring buffer for Kuldhara"
    }
}


def generate_polygonal_buffer(lon, lat, radius_km, num_sides, utm_epsg):
    """
    Generate an authentic multi-sided regular polygon in EPSG:4326 around a centroid
    using metric projection in local UTM.
    """
    radius_meters = radius_km * 1000.0

    to_utm = pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{utm_epsg}", always_xy=True)
    to_wgs84 = pyproj.Transformer.from_crs(f"EPSG:{utm_epsg}", "EPSG:4326", always_xy=True)

    utm_x, utm_y = to_utm.transform(lon, lat)

    # Generate regular polygon vertices
    angles = [i * (2 * math.pi / num_sides) for i in range(num_sides)]
    utm_coords = [
        (utm_x + radius_meters * math.cos(ang), utm_y + radius_meters * math.sin(ang))
        for ang in angles
    ]
    utm_coords.append(utm_coords[0])  # Close ring

    # Reproject back to WGS 84 (EPSG:4326)
    wgs_coords = [to_wgs84.transform(x, y) for x, y in utm_coords]
    geos_poly = GeosPolygon(wgs_coords, srid=4326)
    geos_multipoly = MultiPolygon(geos_poly, srid=4326)

    # Metric area in hectares
    projected_geom = geos_multipoly.transform(utm_epsg, clone=True)
    area_ha = round(projected_geom.area / 10000.0, 2)

    return geos_multipoly, area_ha


class Command(BaseCommand):
    help = "Generate and save standard synthetic fallback boundaries for Bhadla and Kuldhara"

    def add_arguments(self, parser):
        parser.add_argument(
            "--village",
            type=str,
            default=None,
            help="Generate specifically for one village (e.g. --village Bhadla or --village Kuldhara)"
        )
        parser.add_argument(
            "--radius-km",
            type=float,
            default=1.5,
            help="Buffer radius in kilometers (default: 1.5 km)"
        )
        parser.add_argument(
            "--sides",
            type=int,
            choices=[8, 12, 16, 24, 32],
            default=16,
            help="Number of polygon sides (e.g. 8 for octagon, 16 for standard buffer; default: 16)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview calculation without committing to PostgreSQL"
        )

    def handle(self, *args, **options):
        target_name = options["village"]
        cli_radius = options["radius_km"]
        cli_sides = options["sides"]
        dry_run = options["dry_run"]

        if target_name:
            keys = [target_name.strip().lower()]
        else:
            keys = ["bhadla", "kuldhara"]

        self.stdout.write("=" * 70)
        self.stdout.write("GENERATING SYNTHETIC FALLBACK MONITORING BOUNDARIES")
        self.stdout.write("=" * 70)

        updated_villages = []

        with transaction.atomic():
            for key in keys:
                village = Village.objects.filter(name__iexact=key).first()
                if not village:
                    self.stdout.write(self.style.WARNING(f"Village '{key}' not found in database. Skipping."))
                    continue

                config = TARGET_FALLBACK_CONFIGS.get(key, {})
                radius_km = cli_radius or config.get("radius_km", 1.5)
                num_sides = cli_sides or config.get("num_sides", 16)
                utm_epsg = config.get("utm_epsg", 32642 if village.location.x < 73.0 else 32643)

                lon = village.location.x
                lat = village.location.y

                multipoly, area_ha = generate_polygonal_buffer(
                    lon=lon,
                    lat=lat,
                    radius_km=radius_km,
                    num_sides=num_sides,
                    utm_epsg=utm_epsg
                )

                village.boundary = multipoly
                village.area_hectares = area_ha

                if not dry_run:
                    village.save(update_fields=["boundary", "area_hectares", "updated_at"])

                self.stdout.write(self.style.SUCCESS(
                    f"✓ {village.name} ({village.district}):\n"
                    f"    Centroid: [{lon:.4f}, {lat:.4f}]\n"
                    f"    Radius: {radius_km:.1f} km ({num_sides}-sided polygon)\n"
                    f"    Area: {area_ha:.2f} hectares (UTM Zone {utm_epsg})\n"
                    f"    Vertices: {len(multipoly[0][0])}"
                ))

                updated_villages.append({
                    "name": village.name,
                    "multipoly": multipoly,
                    "area_ha": area_ha,
                    "radius_km": radius_km,
                    "sides": num_sides
                })

            if dry_run:
                self.stdout.write(self.style.WARNING("\n[DRY RUN] Rolled back transaction. No changes committed."))
                transaction.set_rollback(True)
            else:
                # Synchronize GeoJSON file
                self._sync_geojson(updated_villages)

        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS(
            f"Successfully saved synthetic monitoring boundaries for {len(updated_villages)} village(s) in PostGIS!"
        ))
        self.stdout.write("=" * 70)

    def _sync_geojson(self, updated_villages):
        """Update data/boundaries/rajasthan_pilot_villages.geojson to match PostGIS."""
        geojson_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "boundaries", "rajasthan_pilot_villages.geojson")
        )
        if not os.path.exists(geojson_path):
            return

        try:
            with open(geojson_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for uv in updated_villages:
                vname = uv["name"].lower()
                for feat in data.get("features", []):
                    if feat.get("properties", {}).get("name", "").lower() == vname:
                        feat["geometry"] = json.loads(uv["multipoly"].geojson)
                        feat["properties"]["is_official"] = False
                        feat["properties"]["source"] = f"Synthetic Monitoring Buffer ({uv['radius_km']} km, {uv['sides']}-gon)"
                        feat["properties"]["area_hectares"] = uv["area_ha"]
                        break

            with open(geojson_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f"✓ Synchronized: {os.path.basename(geojson_path)}"))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Could not synchronize GeoJSON file: {exc}"))
