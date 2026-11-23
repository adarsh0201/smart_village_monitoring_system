"""
Django Management Command: acquire_dem

Queries Microsoft Planetary Computer STAC for Copernicus DEM 30m (cop-dem-glo-30),
precisely clips elevation to official PostGIS village MultiPolygon boundaries,
calculates topographic slope (Horn 1981), and aligns both to existing Sentinel data
for U-Net multi-modal ML training.

Usage:
  python backend/manage.py acquire_dem --village Gahmar
  python backend/manage.py acquire_dem --village "Piplantri"
  python backend/manage.py acquire_dem --all
  python backend/manage.py acquire_dem --village Saifai --force
"""

from django.core.management.base import BaseCommand, CommandError
from villages.models import Village
from satellite.services.dem_ingestion import ingest_village_dem


class Command(BaseCommand):
    help = "Download, clip, and process 30m Copernicus DEM and Topographic Slope aligned to Sentinel data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--village",
            type=str,
            help="Name of target village (e.g. 'Gahmar', 'Piplantri')"
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process Copernicus DEM for all villages in database"
        )
        parser.add_argument(
            "--reference",
            type=str,
            default=None,
            help="Optional path to custom reference Sentinel GeoTIFF for spatial alignment"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-download and re-computation even if files already exist on disk"
        )

    def handle(self, *args, **options):
        village_name = options.get("village")
        process_all = options.get("all")
        ref_path = options.get("reference")
        force_refresh = options.get("force", False)

        if not village_name and not process_all:
            raise CommandError("Please specify either --village <name> or --all to process all villages.")

        if process_all:
            villages = list(Village.objects.all().order_by("name"))
            self.stdout.write(f"Initiating Copernicus DEM processing for all {len(villages)} villages...")
        else:
            village = Village.objects.filter(name__iexact=village_name.strip()).first()
            if not village:
                raise CommandError(f"Village '{village_name}' not found in database.")
            villages = [village]

        total = len(villages)
        successes = 0
        failures = 0

        for idx, v in enumerate(villages, start=1):
            self.stdout.write("=" * 80)
            self.stdout.write(f"[{idx}/{total}] COPERNICUS DEM (GLO-30) & TOPOGRAPHIC SLOPE PIPELINE")
            self.stdout.write(f"Target Village: {v.name} ({v.district}, {v.state})")
            self.stdout.write("=" * 80)

            try:
                self.stdout.write(f"Processing DEM and Slope for '{v.name}'...")
                result = ingest_village_dem(
                    village=v,
                    reference_raster_path=ref_path,
                    force_refresh=force_refresh
                )

                prods = result["products"]
                stats = result["statistics"]

                self.stdout.write(self.style.SUCCESS(f"✓ DEM & SLOPE INGESTION COMPLETE FOR '{v.name}'"))
                self.stdout.write(f"  • STAC Tile ID:        {result.get('tile_id')}")
                self.stdout.write(f"  • Native 30m DEM:      {prods['elevation_30m']}")
                self.stdout.write(f"  • Native 30m Slope:    {prods['slope_30m']}")

                elev_30m_stats = stats.get("elevation_30m", {})
                slope_30m_stats = stats.get("slope_30m", {})
                self.stdout.write(
                    f"  • Elevation (30m):     min={elev_30m_stats.get('min')}m, "
                    f"max={elev_30m_stats.get('max')}m, mean={elev_30m_stats.get('mean')}m "
                    f"({elev_30m_stats.get('valid_count'):,} valid cells)"
                )
                self.stdout.write(
                    f"  • Slope (30m):         min={slope_30m_stats.get('min')}°, "
                    f"max={slope_30m_stats.get('max')}°, mean={slope_30m_stats.get('mean')}°"
                )

                if result["aligned_to_sentinel"]:
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ Aligned to {result.get('reference_sensor')} ({result.get('reference_raster')})"
                    ))
                    self.stdout.write(f"    • Aligned Elevation: {prods['elevation_aligned']}")
                    self.stdout.write(f"    • Aligned Slope:     {prods['slope_aligned']}")
                    elev_aln_stats = stats.get("elevation_aligned", {})
                    slope_aln_stats = stats.get("slope_aligned", {})
                    self.stdout.write(
                        f"    • Aligned Grid:      {elev_aln_stats.get('valid_count'):,} valid cells "
                        f"(Mean Elev: {elev_aln_stats.get('mean')}m | Mean Slope: {slope_aln_stats.get('mean')}°)"
                    )
                else:
                    self.stdout.write(self.style.WARNING(
                        "  ! Note: No existing Sentinel raster found for automatic alignment. "
                        "Native 30m GeoTIFFs generated successfully."
                    ))

                successes += 1

            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"✗ Failed processing for '{v.name}': {exc}"))
                failures += 1

        self.stdout.write("=" * 80)
        self.stdout.write(f"Copernicus DEM Batch Run Complete: {successes} succeeded, {failures} failed.")
        self.stdout.write("=" * 80)
