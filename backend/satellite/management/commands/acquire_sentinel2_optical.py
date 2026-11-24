"""
Django Management Command: acquire_sentinel2_optical

Acquires, clips, and processes Sentinel-2 Level-2A optical imagery (B02, B03, B04, B08, B11, B12, SCL)
for a target village. Computes Phase 4 spectral indices (NDVI, NDWI, SAVI, MNDWI) with cloud masking,
and aligns NDVI, NDWI, and SCL rasters to the village reference grid for Phase 8 Random Forest classification.

Usage:
  python backend/manage.py acquire_sentinel2_optical --village Gahmar
  python backend/manage.py acquire_sentinel2_optical --village Piplantri --max-cloud 20.0
  python backend/manage.py acquire_sentinel2_optical --village Saifai --force
  python backend/manage.py acquire_sentinel2_optical --all
"""

import os
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone

from villages.models import Village
from satellite.models import SatelliteScene, SpectralIndex
from satellite.services.search import search_sentinel2_scenes
from satellite.services.ingestion import ingest_sentinel2_scene
from satellite.services.indices import compute_scene_indices
from ml.train_random_forest import derive_and_align_optical_indices, resolve_village_instance

logger = logging.getLogger("satellite.optical")


class Command(BaseCommand):
    help = (
        "Acquire and process Sentinel-2 Level-2A optical bands (B02, B03, B04, B08, B11, B12, SCL), "
        "compute Phase 4 spectral indices (NDVI, NDWI, SAVI, MNDWI), and align optical rasters for ML."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--village",
            type=str,
            default=None,
            help="Name or ID of the village to process (e.g. 'Gahmar', 'Piplantri')"
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Acquire and process Sentinel-2 optical data for all villages in database"
        )
        parser.add_argument(
            "--scene-id",
            type=str,
            default=None,
            help="Specific Sentinel-2 scene ID to acquire (defaults to cleanest available)"
        )
        parser.add_argument(
            "--max-cloud",
            type=float,
            default=25.0,
            help="Maximum scene cloud cover percentage (default: 25.0)"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-download and re-computation even if optical rasters already exist"
        )

    def handle(self, *args, **options):
        village_name = options.get("village")
        process_all = options.get("all")
        scene_id = options.get("scene_id")
        max_cloud = options.get("max_cloud", 25.0)
        force_refresh = options.get("force", False)

        if not village_name and not process_all:
            raise CommandError("Please specify either --village <name/id> or --all to process all villages.")

        if process_all:
            villages = list(Village.objects.all().order_by("id"))
            self.stdout.write("=" * 80)
            self.stdout.write(f"BULK SENTINEL-2 OPTICAL & SPECTRAL INDICES ACQUISITION ({len(villages)} VILLAGES)")
            self.stdout.write("=" * 80)
            success_count, fail_count = 0, 0
            for idx, v in enumerate(villages, start=1):
                self.stdout.write(f"\n[{idx}/{len(villages)}] Processing '{v.name}' (ID: {v.id})...")
                try:
                    self.process_village(v, scene_id=None, max_cloud=max_cloud, force_refresh=force_refresh)
                    success_count += 1
                except Exception as exc:
                    fail_count += 1
                    self.stdout.write(self.style.WARNING(f"  [!] Failed for '{v.name}': {exc}"))
                    logger.warning(f"Error processing optical data for {v.name}: {exc}", exc_info=True)
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.SUCCESS(f"Complete: {success_count} succeeded, {fail_count} failed."))
            self.stdout.write("=" * 80)
        else:
            try:
                village = resolve_village_instance(village_name)
            except Exception:
                village = Village.objects.filter(name__iexact=village_name.strip()).first()
                if not village and village_name.isdigit():
                    village = Village.objects.filter(pk=int(village_name)).first()
            if not village:
                raise CommandError(f"Village '{village_name}' not found in database.")

            self.stdout.write("=" * 80)
            self.stdout.write("PHASE 4 & 8: SENTINEL-2 OPTICAL ACQUISITION & SPECTRAL INDICES")
            v_state = getattr(village, "state", "Uttar Pradesh")
            v_dist = getattr(village, "district", "Unknown")
            self.stdout.write(f"Target Village: {village.name} ({v_dist}, {v_state})")
            self.stdout.write("=" * 80)
            self.process_village(village, scene_id=scene_id, max_cloud=max_cloud, force_refresh=force_refresh)

    def process_village(self, village, scene_id=None, max_cloud=25.0, force_refresh=False):
        optical_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "optical", f"village_{village.id}")
        ndvi_p = os.path.join(optical_dir, "NDVI.tif")
        ndwi_p = os.path.join(optical_dir, "NDWI.tif")
        scl_p = os.path.join(optical_dir, "SCL.tif")

        # 1. Idempotency Check
        has_aligned_optical = (
            os.path.isfile(ndvi_p) and os.path.isfile(ndwi_p) and os.path.isfile(scl_p)
        )
        existing_scene = (
            SatelliteScene.objects.filter(village=village, status="completed", collection="sentinel-2-l2a").first()
            or SatelliteScene.objects.filter(village=village, status="completed", scene_id__istartswith="S2").first()
        )

        if has_aligned_optical and existing_scene and not force_refresh:
            indices_count = SpectralIndex.objects.filter(scene=existing_scene).count()
            if indices_count >= 2:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [✓] Optical rasters (NDVI, NDWI, SCL) and {indices_count} spectral indices "
                        f"already exist on disk for '{village.name}' (Scene: {existing_scene.scene_id})."
                    )
                )
                return

        # 2. Scene Discovery
        if not scene_id:
            self.stdout.write(f"Searching STAC for low-cloud Sentinel-2 scenes over '{village.name}'...")
            now = timezone.now()
            start_date = (now - timedelta(days=180)).strftime("%Y-%m-%d")

            search_res = search_sentinel2_scenes(
                village=village,
                start_date=start_date,
                max_cloud_cover=max_cloud,
                limit=10,
                buffer_km=2.5
            )
            scenes = search_res.get("scenes", [])

            # Broaden search if no scenes meet strict criteria
            if not scenes:
                self.stdout.write("  • No scenes found in last 180 days below cloud threshold; broadening search...")
                search_res = search_sentinel2_scenes(
                    village=village,
                    start_date="2023-01-01",
                    max_cloud_cover=100.0,
                    limit=20,
                    buffer_km=2.5
                )
                scenes = search_res.get("scenes", [])

            if not scenes:
                raise CommandError(f"No Sentinel-2 Level-2A optical scenes found intersecting {village.name}.")

            # Prefer scenes with required bands available, sorted by lowest cloud cover
            valid_scenes = [s for s in scenes if s.get("required_bands_available", True)] or scenes
            valid_scenes.sort(key=lambda s: s.get("cloud_cover", 100.0))
            selected_scene = valid_scenes[0]
            scene_id = selected_scene["scene_id"]
            self.stdout.write(
                f"  ✓ Selected scene: {scene_id} "
                f"(Date: {selected_scene.get('acquisition_date', '')[:10]} | Cloud: {selected_scene.get('cloud_cover', 0)}%)"
            )
        else:
            self.stdout.write(f"Using explicitly specified Sentinel-2 scene: {scene_id}")

        # 3. Ingest Sentinel-2 Bands (B02, B03, B04, B08, B11, B12, SCL)
        self.stdout.write(f"Downloading and window-clipping Sentinel-2 Level-2A bands for '{village.name}'...")
        ingest_res = ingest_sentinel2_scene(
            village=village,
            scene_id=scene_id,
            buffer_km=2.5,
            force_refresh=force_refresh
        )
        scene_record = ingest_res["scene"]
        self.stdout.write(self.style.SUCCESS(f"  ✓ Bands downloaded & clipped to AOI ({scene_record.bands.count()} bands)"))

        # 4. Compute Spectral Indices (NDVI, NDWI, SAVI, MNDWI) with SCL Cloud Masking
        self.stdout.write(f"Computing Phase 4 spectral indices (NDVI, NDWI, SAVI, MNDWI) for '{village.name}'...")
        idx_res = compute_scene_indices(
            scene=scene_record,
            mask_clouds=True,
            overwrite=force_refresh
        )
        computed_count = len(idx_res.get("indices", []))
        self.stdout.write(self.style.SUCCESS(f"  ✓ Computed {computed_count} spectral indices with cloud masking"))

        # 5. Derive Aligned Optical Rasters (NDVI.tif, NDWI.tif, SCL.tif) for ML
        s2_raw_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "villages", str(village.id))
        ref_path = None

        # Check Copernicus DEM elevation first
        dem_elev = os.path.join(settings.MEDIA_ROOT, "satellite", "dem", f"village_{village.id}", "elevation_aligned.tif")
        if os.path.isfile(dem_elev):
            ref_path = dem_elev
        else:
            # Check SAR VV_db.tif
            sar_dir = os.path.join(settings.MEDIA_ROOT, "satellite", "sar", f"village_{village.id}")
            if os.path.isdir(sar_dir):
                for root, _, files in os.walk(sar_dir):
                    if "VV_db.tif" in files:
                        ref_path = os.path.join(root, "VV_db.tif")
                        break

        if ref_path and os.path.isfile(ref_path) and os.path.isdir(s2_raw_dir):
            self.stdout.write(f"Deriving and aligning 10m UTM optical rasters (NDVI, NDWI, SCL) for ML...")
            try:
                derived = derive_and_align_optical_indices(
                    village=village,
                    s2_raw_dir=s2_raw_dir,
                    ref_raster_path=ref_path,
                    optical_dir=optical_dir
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Saved aligned optical features in {optical_dir}:\n"
                        f"      • {os.path.basename(derived['ndvi'])}\n"
                        f"      • {os.path.basename(derived['ndwi'])}\n"
                        f"      • {os.path.basename(derived['scl'])}"
                    )
                )
            except Exception as align_exc:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [!] Note: Immediate optical grid alignment deferred ({align_exc}). "
                        f"train_rf_model will align automatically."
                    )
                )
        else:
            self.stdout.write(
                "  • Reference grid (DEM/SAR) not yet on disk; "
                "train_rf_model will derive and align NDVI/NDWI/SCL once DEM is acquired."
            )

        self.stdout.write(self.style.SUCCESS(f"✓ Optical acquisition and spectral indices complete for '{village.name}'."))
