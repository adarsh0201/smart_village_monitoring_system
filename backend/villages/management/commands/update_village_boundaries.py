import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.conf import settings

from villages.models import Village


class Command(BaseCommand):
    help = (
        "Read a GeoJSON file containing village boundary MultiPolygons "
        "and update the spatial boundary and area fields in the PostGIS Village model."
    )

    def add_arguments(self, parser):
        default_geojson = os.path.abspath(
            os.path.join(settings.BASE_DIR, "..", "data", "boundaries", "rajasthan_pilot_villages.geojson")
        )
        parser.add_argument(
            "--geojson",
            type=str,
            default=default_geojson,
            help=f"Path to the input GeoJSON file (default: {default_geojson})"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate geometries and log proposed updates without saving to the database."
        )

    def handle(self, *args, **options):
        geojson_path = os.path.abspath(options["geojson"])
        dry_run = options["dry_run"]

        self.stdout.write(self.style.NOTICE("=" * 70))
        self.stdout.write(self.style.NOTICE("VILLAGE BOUNDARY UPDATE (GEODJANGO + POSTGIS)"))
        self.stdout.write(self.style.NOTICE(f"Source GeoJSON: {geojson_path}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE: No database changes will be committed."))
        self.stdout.write(self.style.NOTICE("=" * 70))

        if not os.path.exists(geojson_path):
            raise CommandError(f"GeoJSON file not found at: {geojson_path}")

        try:
            with open(geojson_path, "r", encoding="utf-8") as f:
                geojson_data = json.load(f)
        except Exception as exc:
            raise CommandError(f"Failed to read/parse GeoJSON: {exc}")

        features = geojson_data.get("features", [])
        if not features:
            self.stdout.write(self.style.WARNING("No features found in GeoJSON. Exiting."))
            return

        self.stdout.write(f"Found {len(features)} feature(s) in GeoJSON.\n")

        # UTM zone mapping for Rajasthan:
        # Western Rajasthan (Phalodi, Jaisalmer, Jodhpur) -> EPSG:32642 (UTM Zone 42N)
        # Central/Eastern Rajasthan (Rajsamand, Jhunjhunu, Jaipur) -> EPSG:32643 (UTM Zone 43N)
        utm_mapping = {
            "Phalodi": 32642,
            "Jaisalmer": 32642,
            "Bikaner": 32642,
            "Barmer": 32642,
            "Rajsamand": 32643,
            "Jhunjhunu": 32643,
            "Udaipur": 32643,
            "Jaipur": 32643,
        }

        updated_count = 0
        skipped_count = 0
        error_count = 0

        with transaction.atomic():
            for idx, feature in enumerate(features, start=1):
                props = feature.get("properties", {})
                geom_data = feature.get("geometry")

                # Extract village identifier
                v_name = props.get("name") or props.get("village_name")
                v_district = props.get("district")
                is_official = props.get("is_official", True)

                if not v_name:
                    self.stdout.write(self.style.ERROR(f"  [{idx}] Feature missing 'name' property. Skipping."))
                    skipped_count += 1
                    continue

                if not geom_data:
                    self.stdout.write(self.style.ERROR(f"  [{idx}] Village '{v_name}' has null geometry. Skipping."))
                    skipped_count += 1
                    continue

                # Locate Village in PostgreSQL/PostGIS
                village_query = Village.objects.filter(name__iexact=v_name)
                if v_district:
                    village = village_query.filter(district__iexact=v_district).first() or village_query.first()
                else:
                    village = village_query.first()

                if not village:
                    self.stdout.write(self.style.WARNING(
                        f"  [{idx}] Village '{v_name}' not found in database. Skipping."
                    ))
                    skipped_count += 1
                    continue

                # Parse geometry via GeoDjango GEOSGeometry
                try:
                    geos_geom = GEOSGeometry(json.dumps(geom_data), srid=4326)
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(
                        f"  [{idx}] Invalid geometry for '{v_name}': {exc}"
                    ))
                    error_count += 1
                    continue

                if not geos_geom.valid:
                    self.stdout.write(self.style.WARNING(
                        f"  [{idx}] Geometry for '{v_name}' is invalid ({geos_geom.valid_reason}). Attempting ST_MakeValid repair..."
                    ))
                    geos_geom = geos_geom.valid_reason  # In Django, GEOSGeometry.make_valid()
                    try:
                        geos_geom = geos_geom.make_valid()
                    except AttributeError:
                        pass

                # Enforce MultiPolygon standard
                if geos_geom.geom_type == "Polygon":
                    multi_poly = MultiPolygon([geos_geom], srid=4326)
                elif geos_geom.geom_type == "MultiPolygon":
                    multi_poly = geos_geom
                else:
                    self.stdout.write(self.style.ERROR(
                        f"  [{idx}] Unsupported geometry type '{geos_geom.geom_type}' for '{v_name}'. Must be (Multi)Polygon."
                    ))
                    error_count += 1
                    continue

                # Compute accurate area in hectares via projected UTM transformation
                utm_epsg = utm_mapping.get(village.district, 32643)
                try:
                    geom_utm = multi_poly.transform(utm_epsg, clone=True)
                    calc_area_ha = round(geom_utm.area / 10000.0, 2)
                except Exception:
                    calc_area_ha = village.area_hectares

                # Update model instance
                village.boundary = multi_poly
                if calc_area_ha and calc_area_ha > 0:
                    village.area_hectares = calc_area_ha

                if not dry_run:
                    village.save()

                status_label = "OFFICIAL" if is_official else "PROVISIONAL/CADASTRAL"
                self.stdout.write(self.style.SUCCESS(
                    f"  [+] Updated '{village.name}' ({village.district}): "
                    f"MultiPolygon ({len(multi_poly)} sub-polys), Area: {village.area_hectares} ha [{status_label}]"
                ))
                updated_count += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS(
            f"SUMMARY: {updated_count} village(s) updated, {skipped_count} skipped, {error_count} error(s)."
        ))
        self.stdout.write(self.style.NOTICE("=" * 70))

