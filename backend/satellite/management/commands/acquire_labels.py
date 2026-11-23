"""
Django Management Command: acquire_labels

Queries Microsoft Planetary Computer STAC for ESA WorldCover 10m (esa-worldcover),
clips the ground truth LULC mask to official PostGIS village MultiPolygon boundaries,
reprojects and aligns the categorical labels to the exact UTM coordinate grid and
affine transform of existing Sentinel / DEM data using Resampling.nearest,
and outputs worldcover_aligned.tif as the y target mask for U-Net ML training.

Usage:
  python backend/manage.py acquire_labels --village Gahmar
  python backend/manage.py acquire_labels --village Piplantri
  python backend/manage.py acquire_labels --all
  python backend/manage.py acquire_labels --village Saifai --force
"""

from django.core.management.base import BaseCommand, CommandError
from villages.models import Village
from satellite.services.worldcover_ingestion import ingest_worldcover_labels, ESA_WORLDCOVER_CLASSES


class Command(BaseCommand):
    help = "Download, clip, and align 10m ESA WorldCover ground truth labels for U-Net training"

    def add_arguments(self, parser):
        parser.add_argument(
            "--village",
            type=str,
            help="Name of target village (e.g. 'Gahmar', 'Piplantri')"
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process ESA WorldCover labels for all villages in database"
        )
        parser.add_argument(
            "--year",
            type=int,
            default=2021,
            choices=[2020, 2021],
            help="WorldCover product year: 2021 (v200, recommended) or 2020 (v100)"
        )
        parser.add_argument(
            "--reference",
            type=str,
            default=None,
            help="Optional path to custom reference Sentinel/DEM GeoTIFF for spatial alignment"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-download and re-alignment even if files already exist on disk"
        )

    def handle(self, *args, **options):
        village_name = options.get("village")
        process_all = options.get("all")
        year = options.get("year", 2021)
        ref_path = options.get("reference")
        force_refresh = options.get("force", False)

        if not village_name and not process_all:
            raise CommandError("Please specify either --village <name> or --all to process all villages.")

        if process_all:
            villages = list(Village.objects.all().order_by("name"))
            self.stdout.write(f"Initiating ESA WorldCover label acquisition for all {len(villages)} villages...")
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
            self.stdout.write(f"[{idx}/{total}] ESA WORLDCOVER 10M GROUND TRUTH LABEL PIPELINE")
            self.stdout.write(f"Target Village: {v.name} ({v.district}, {v.state}) | Edition: {year}")
            self.stdout.write("=" * 80)

            try:
                self.stdout.write(f"Acquiring and aligning WorldCover labels for '{v.name}'...")
                result = ingest_worldcover_labels(
                    village=v,
                    reference_raster_path=ref_path,
                    year=year,
                    force_refresh=force_refresh
                )

                dist = result["distribution"]
                classes = dist.get("classes", {})

                self.stdout.write(self.style.SUCCESS(f"✓ WORLDCOVER LABELS ACQUIRED & ALIGNED FOR '{v.name}'"))
                self.stdout.write(f"  • STAC Tile ID:        {result.get('tile_id')}")
                self.stdout.write(f"  • Aligned Label Mask:  {result.get('label_path')}")
                self.stdout.write(f"  • Spatial Grid:        {result.get('width')} x {result.get('height')} px "
                                  f"({result.get('crs')} @ {result.get('resolution')[0]}m)")
                self.stdout.write(f"  • Alignment Reference: {result.get('aligned_to_sensor')} "
                                  f"({result.get('reference_raster')})")
                self.stdout.write(f"  • Resampling Method:   Resampling.nearest (Categorical Preserved)")
                self.stdout.write(f"  • Labeled Pixels (y):  {dist.get('valid_pixels'):,} valid cells")

                self.stdout.write("\n  --- Land Cover Class Breakdown (Ground Truth Target) ---")
                for cls_id in sorted(classes.keys()):
                    info = classes[cls_id]
                    self.stdout.write(
                        f"    [{cls_id:3d}] {info['name']:<24}: "
                        f"{info['pixel_count']:>7,} px ({info['percentage']:>5.2f}%) | "
                        f"{info['area_hectares']:>7.2f} ha"
                    )

                successes += 1

            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"✗ Failed processing for '{v.name}': {exc}"))
                failures += 1

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"ESA WorldCover Label Run Complete: {successes} succeeded, {failures} failed.")
        self.stdout.write("=" * 80)
