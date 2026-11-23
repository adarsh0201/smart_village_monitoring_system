"""
Django Management Command: acquire_sentinel1_sar

Acquires, clips, and processes Sentinel-1 SAR dual-polarization imagery (VV & VH)
for a target village. Performs radiometric calibration to decibels (dB), calculates
the Dual-Pol Cross Ratio (VH/VV) and Radar Vegetation Index (RVI), and persists
records and statistics to PostgreSQL/PostGIS.
"""

from django.core.management.base import BaseCommand, CommandError
from villages.models import Village
from satellite.services.sar_search import search_sentinel1_sar_scenes
from satellite.services.sar_ingestion import ingest_sentinel1_sar_scene


class Command(BaseCommand):
    help = "Acquire and process Sentinel-1 SAR imagery (VV, VH, Cross-Ratio, RVI) for a target village"

    def add_arguments(self, parser):
        parser.add_argument(
            "--village",
            type=str,
            default="Gahmar",
            help="Name of the village to process (default: Gahmar)"
        )
        parser.add_argument(
            "--scene-id",
            type=str,
            default=None,
            help="Specific Sentinel-1 scene ID to acquire (defaults to latest available)"
        )
        parser.add_argument(
            "--orbit",
            type=str,
            choices=["ascending", "descending", "any"],
            default="any",
            help="Satellite orbit pass direction (default: any)"
        )
        parser.add_argument(
            "--collection",
            type=str,
            choices=["sentinel-1-rtc", "sentinel-1-grd"],
            default="sentinel-1-rtc",
            help="SAR STAC collection: 'sentinel-1-rtc' (Terrain-Corrected, recommended) or 'sentinel-1-grd'"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-processing and overwrite existing cached raster products"
        )

    def handle(self, *args, **options):
        village_name = options["village"]
        scene_id = options["scene_id"]
        collection = options["collection"]
        orbit = None if options["orbit"] == "any" else options["orbit"]
        force_refresh = options["force"]

        village = Village.objects.filter(name__iexact=village_name).first()
        if not village:
            raise CommandError(f"Village '{village_name}' not found in database.")

        self.stdout.write("=" * 80)
        self.stdout.write(f"PHASE 2: SENTINEL-1 SAR ACQUISITION & PROCESSING")
        self.stdout.write(f"Target Village: {village.name} ({village.district}, {village.state})")
        self.stdout.write(f"Collection:     {collection}")
        self.stdout.write("=" * 80)

        # 1. Discover or Resolve Target Scene
        vv_url, vh_url = None, None
        if not scene_id:
            self.stdout.write(f"Searching STAC for latest Sentinel-1 scenes over {village.name}...")
            scenes = search_sentinel1_sar_scenes(
                village=village,
                limit=5,
                orbit_direction=orbit,
                collection=collection,
                sign_urls=True
            )
            # Fallback to alternate collection if not found
            if not scenes and collection == "sentinel-1-rtc":
                self.stdout.write("No RTC scenes found, attempting fallback to sentinel-1-grd...")
                collection = "sentinel-1-grd"
                scenes = search_sentinel1_sar_scenes(
                    village=village,
                    limit=5,
                    orbit_direction=orbit,
                    collection=collection,
                    sign_urls=True
                )

            if not scenes:
                raise CommandError(f"No Sentinel-1 SAR scenes found intersecting {village.name}.")

            selected_scene = scenes[0]
            scene_id = selected_scene["scene_id"]
            assets = selected_scene.get("assets", {})
            vv_url = assets.get("vv") or assets.get("VV")
            vh_url = assets.get("vh") or assets.get("VH")
            self.stdout.write(
                f"✓ Selected latest scene: {scene_id} "
                f"({selected_scene['acquisition_date'][:10]} | Orbit: {selected_scene['orbit_state']})"
            )
        else:
            self.stdout.write(f"Using explicitly specified scene ID: {scene_id}")

        # 2. Ingest & Process SAR Imagery
        self.stdout.write(f"\nProcessing dual-pol radar imagery for {village.name}...")
        self.stdout.write("  - Fetching official PostGIS MultiPolygon boundary...")
        self.stdout.write("  - Streaming & clipping VV and VH Cloud-Optimized GeoTIFFs (rasterio.mask)...")
        self.stdout.write("  - Calibrating linear DN to backscatter coefficient sigma_0 (dB)...")
        self.stdout.write("  - Computing Dual-Pol Cross-Ratio (VH_dB - VV_dB)...")
        self.stdout.write("  - Computing Radar Vegetation Index (RVI)...")

        result = ingest_sentinel1_sar_scene(
            village=village,
            scene_id=scene_id,
            vv_asset_url=vv_url,
            vh_asset_url=vh_url,
            force_refresh=force_refresh
        )

        manifest = result.get("manifest", {})
        stats = manifest.get("statistics", {})

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(f"✓ ACQUISITION & PROCESSING COMPLETE FOR '{village.name}'"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Status:          {'CACHED (Already on disk)' if result.get('cached') else 'PROCESSED & COMMITTED'}")
        self.stdout.write(f"Scene ID:        {scene_id}")
        self.stdout.write(f"Output Products:")
        if manifest:
            self.stdout.write(f"  • VV (dB):       {manifest.get('vv_path')}")
            self.stdout.write(f"  • VH (dB):       {manifest.get('vh_path')}")
            self.stdout.write(f"  • Cross-Ratio:   {manifest.get('cross_ratio_path')}")
            self.stdout.write(f"  • RVI:           {manifest.get('rvi_path')}")

        if stats:
            cr_stat = stats.get("cross_ratio_db", {})
            vv_stat = stats.get("vv_db", {})
            vh_stat = stats.get("vh_db", {})
            self.stdout.write("\nRadar Backscatter Summary:")
            self.stdout.write(f"  • Mean VV Backscatter:   {vv_stat.get('mean', 'N/A')} dB")
            self.stdout.write(f"  • Mean VH Backscatter:   {vh_stat.get('mean', 'N/A')} dB")
            self.stdout.write(f"  • Mean Dual-Pol Ratio:   {cr_stat.get('mean', 'N/A')} dB")
            self.stdout.write(f"  • Valid Pixels Analyzed: {cr_stat.get('valid_count', 'N/A'):,}")
        self.stdout.write("=" * 80)
