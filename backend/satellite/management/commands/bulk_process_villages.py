"""
Django Management Command: bulk_process_villages

Automates the complete multi-modal Earth Observation & AI LULC pipeline for all
registered villages (or a targeted subset) in the PostgreSQL/PostGIS database.

Sequentially executes for each village:
1. acquire_sentinel1_sar (Sentinel-1 RTC Dual-Pol Backscatter, Cross-Ratio, RVI)
2. acquire_dem (Copernicus DEM 30m GLO-30 & Topographic Slope)
3. acquire_labels (ESA WorldCover 10m Ground Truth Masks via nearest-neighbor)
4. train_rf_model --predict (Phase 8 6-Feature Random Forest Training & 2D GeoTIFF Inference)

Includes robust error-handling, progress telemetry, resume capability, and summary reporting.

Usage:
  python backend/manage.py bulk_process_villages
  python backend/manage.py bulk_process_villages --dry-run
  python backend/manage.py bulk_process_villages --exclude Gahmar
  python backend/manage.py bulk_process_villages --village Piplantri
  python backend/manage.py bulk_process_villages --start-from 5
  python backend/manage.py bulk_process_villages --force
"""

import os
import sys
import time
import logging
import traceback
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from villages.models import Village

logger = logging.getLogger("satellite.bulk_processing")


class Command(BaseCommand):
    help = (
        "Bulk orchestrator: Sequentially acquires SAR, DEM, ESA WorldCover labels, "
        "and trains the 6-feature Random Forest model with 2D prediction for all villages."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--village",
            type=str,
            default=None,
            help="Process a single village by name or ID (e.g. --village Piplantri or --village 1)"
        )
        parser.add_argument(
            "--exclude",
            type=str,
            default=None,
            help="Comma-separated list of village names or IDs to skip (e.g. --exclude 'Gahmar,Piplantri')"
        )
        parser.add_argument(
            "--start-from",
            type=str,
            default=None,
            help="Resume processing starting from a specific village name or ID"
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of villages to process in this run"
        )
        parser.add_argument(
            "--steps",
            type=str,
            default="sar,dem,labels,train",
            help="Comma-separated pipeline stages to run: sar,dem,labels,train (default: all 4)"
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-acquisition and re-training even if prediction TIFF already exists"
        )
        parser.add_argument(
            "--stop-on-error",
            action="store_true",
            help="Halt the entire bulk run immediately if any step fails (default: continue to next village)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Scan and report target villages and asset status without executing downloads or training"
        )

    def handle(self, *args, **options):
        single_target = options.get("village")
        exclude_arg = options.get("exclude")
        start_from = options.get("start_from")
        limit = options.get("limit")
        steps_arg = options.get("steps", "sar,dem,labels,train").lower()
        force_refresh = options.get("force", False)
        stop_on_error = options.get("stop_on_error", False)
        is_dry_run = options.get("dry_run", False)

        active_steps = [s.strip() for s in steps_arg.split(",") if s.strip()]

        # 1. Query target villages
        qs = Village.objects.all().order_by("id")

        if single_target:
            if single_target.isdigit():
                qs = qs.filter(pk=int(single_target))
            else:
                qs = qs.filter(name__iexact=single_target.strip())
            if not qs.exists():
                raise CommandError(f"Target village '{single_target}' not found in database.")

        villages_list = list(qs)
        total_in_db = len(villages_list)

        # Handle exclusion list
        excluded_names = set()
        if exclude_arg:
            for item in exclude_arg.split(","):
                clean = item.strip().lower()
                if clean:
                    excluded_names.add(clean)

        # Handle start-from resuming
        if start_from:
            start_clean = str(start_from).strip().lower()
            start_idx = None
            for idx, v in enumerate(villages_list):
                if str(v.id) == start_clean or v.name.lower() == start_clean:
                    start_idx = idx
                    break
            if start_idx is not None:
                villages_list = villages_list[start_idx:]
                self.stdout.write(f"Resuming bulk pipeline from index {start_idx + 1} ({start_from})...")
            else:
                self.stdout.write(self.style.WARNING(f"Start-from identifier '{start_from}' not found; starting from beginning."))

        if limit and limit > 0:
            villages_list = villages_list[:limit]

        # Filter out excluded villages
        filtered_villages = []
        for v in villages_list:
            if v.name.lower() in excluded_names or str(v.id) in excluded_names:
                continue
            filtered_villages.append(v)

        total_to_process = len(filtered_villages)

        self.stdout.write("=" * 80)
        self.stdout.write("SMART VILLAGE BULK MULTI-MODAL PROCESSING ENGINE")
        self.stdout.write("=" * 80)
        self.stdout.write(f"• Total Villages in Database:  {total_in_db}")
        self.stdout.write(f"• Selected for Processing:     {total_to_process}")
        self.stdout.write(f"• Pipeline Stages to Execute:  {', '.join(active_steps).upper()}")
        self.stdout.write(f"• Force Overwrite Mode:        {force_refresh}")
        self.stdout.write(f"• Error Policy:                {'Stop on first error' if stop_on_error else 'Skip failed village & continue'}")
        if is_dry_run:
            self.stdout.write(self.style.WARNING("• Execution Mode:              DRY RUN (Inspection only, no disk writes)"))
        self.stdout.write("=" * 80)

        if total_to_process == 0:
            self.stdout.write(self.style.WARNING("No villages selected for processing. Exiting."))
            return

        # Dry Run Mode: Print audit checklist and return
        if is_dry_run:
            self.stdout.write("\nTarget Villages Audit Checklist:")
            for idx, v in enumerate(filtered_villages, start=1):
                pred_path = os.path.join(settings.MEDIA_ROOT, "satellite", "worldcover", f"village_{v.id}", "rf_predicted_lulc.tif")
                has_pred = os.path.isfile(pred_path)
                status_icon = "✓ COMPLETE" if has_pred else "• PENDING"
                self.stdout.write(f"  [{idx:2d}/{total_to_process:2d}] ID: {v.id:2d} | {v.name:<24} | {v.district:<16} | {status_icon}")
            self.stdout.write("\nDry run completed. Run without --dry-run to begin bulk processing.")
            return

        # 2. Execution Loop
        start_time_all = time.time()
        summary = {
            "success": [],
            "failed": [],
            "skipped": [],
        }

        for idx, v in enumerate(filtered_villages, start=1):
            v_start = time.time()
            self.stdout.write("\n" + "-" * 80)
            self.stdout.write(
                self.style.MIGRATE_HEADING(
                    f"[{idx}/{total_to_process}] Processing Village: {v.name} (ID: {v.id}, {v.district}, {v.state})"
                )
            )
            self.stdout.write("-" * 80)

            # Check if village is already completed
            pred_path = os.path.join(settings.MEDIA_ROOT, "satellite", "worldcover", f"village_{v.id}", "rf_predicted_lulc.tif")
            if os.path.isfile(pred_path) and not force_refresh:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [✓] rf_predicted_lulc.tif already exists for '{v.name}'. Skipping (use --force to re-process)."
                    )
                )
                summary["skipped"].append({"id": v.id, "name": v.name, "reason": "Already processed"})
                continue

            village_failed = False
            failed_stage = None
            error_details = None

            # Stage 1: Sentinel-1 SAR Acquisition & Calibration
            if "sar" in active_steps and not village_failed:
                self.stdout.write(f"\n  [Stage 1/4] Running acquire_sentinel1_sar for '{v.name}'...")
                try:
                    call_command("acquire_sentinel1_sar", village=v.name, force=force_refresh)
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Sentinel-1 SAR acquisition complete for '{v.name}'"))
                except Exception as exc:
                    village_failed = True
                    failed_stage = "acquire_sentinel1_sar"
                    error_details = str(exc)
                    self.stdout.write(self.style.WARNING(f"  [!] Stage 1 Failed for '{v.name}': {exc}"))
                    logger.warning(f"Bulk pipeline Stage 1 error for {v.name}: {exc}", exc_info=True)

            # Stage 2: Copernicus DEM 30m & Topographic Slope
            if "dem" in active_steps and not village_failed:
                self.stdout.write(f"\n  [Stage 2/4] Running acquire_dem for '{v.name}'...")
                try:
                    call_command("acquire_dem", village=v.name, force=force_refresh)
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Copernicus DEM & Slope complete for '{v.name}'"))
                except Exception as exc:
                    village_failed = True
                    failed_stage = "acquire_dem"
                    error_details = str(exc)
                    self.stdout.write(self.style.WARNING(f"  [!] Stage 2 Failed for '{v.name}': {exc}"))
                    logger.warning(f"Bulk pipeline Stage 2 error for {v.name}: {exc}", exc_info=True)

            # Stage 3: ESA WorldCover 10m Ground Truth Labels
            if "labels" in active_steps and not village_failed:
                self.stdout.write(f"\n  [Stage 3/4] Running acquire_labels for '{v.name}'...")
                try:
                    call_command("acquire_labels", village=v.name, force=force_refresh)
                    self.stdout.write(self.style.SUCCESS(f"  ✓ ESA WorldCover labels aligned for '{v.name}'"))
                except Exception as exc:
                    village_failed = True
                    failed_stage = "acquire_labels"
                    error_details = str(exc)
                    self.stdout.write(self.style.WARNING(f"  [!] Stage 3 Failed for '{v.name}': {exc}"))
                    logger.warning(f"Bulk pipeline Stage 3 error for {v.name}: {exc}", exc_info=True)

            # Stage 4: 6-Feature Random Forest Training & 2D Prediction
            if "train" in active_steps and not village_failed:
                self.stdout.write(f"\n  [Stage 4/4] Training Random Forest & predicting 2D LULC for '{v.name}'...")
                try:
                    call_command("train_rf_model", village=v.name, predict=True)
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Model trained and rf_predicted_lulc.tif exported for '{v.name}'"))
                except Exception as exc:
                    village_failed = True
                    failed_stage = "train_rf_model"
                    error_details = str(exc)
                    self.stdout.write(self.style.WARNING(f"  [!] Stage 4 Failed for '{v.name}': {exc}"))
                    logger.warning(f"Bulk pipeline Stage 4 error for {v.name}: {exc}", exc_info=True)

            v_elapsed = time.time() - v_start

            if village_failed:
                summary["failed"].append({
                    "id": v.id,
                    "name": v.name,
                    "stage": failed_stage,
                    "error": error_details,
                    "elapsed": v_elapsed
                })
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Village '{v.name}' failed at stage [{failed_stage}] after {v_elapsed:.1f}s."
                    )
                )
                if stop_on_error:
                    self.stdout.write(self.style.ERROR("\nAborting bulk execution due to --stop-on-error flag."))
                    break
            else:
                summary["success"].append({
                    "id": v.id,
                    "name": v.name,
                    "elapsed": v_elapsed
                })
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Completed all stages for '{v.name}' in {v_elapsed:.1f}s!"
                    )
                )

        # 3. Final Summary Report
        total_elapsed = time.time() - start_time_all
        elapsed_str = str(timedelta(seconds=int(total_elapsed)))

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("BULK PIPELINE EXECUTION SUMMARY")
        self.stdout.write("=" * 80)
        self.stdout.write(f"• Total Runtime:   {elapsed_str} ({total_elapsed:.1f}s)")
        self.stdout.write(f"• Total Targeted:  {total_to_process} villages")
        self.stdout.write(self.style.SUCCESS(f"• Succeeded:       {len(summary['success'])}"))
        self.stdout.write(f"• Skipped:         {len(summary['skipped'])}")
        if summary["failed"]:
            self.stdout.write(self.style.ERROR(f"• Failed:          {len(summary['failed'])}"))
        else:
            self.stdout.write(self.style.SUCCESS("• Failed:          0"))

        if summary["success"]:
            self.stdout.write("\nSuccessfully Processed Villages:")
            for item in summary["success"]:
                self.stdout.write(f"  ✓ ID: {item['id']:2d} | {item['name']:<24} | {item['elapsed']:.1f}s")

        if summary["skipped"]:
            self.stdout.write("\nSkipped Villages (Already Completed):")
            for item in summary["skipped"]:
                self.stdout.write(f"  • ID: {item['id']:2d} | {item['name']:<24} | {item['reason']}")

        if summary["failed"]:
            self.stdout.write("\nFailed Villages:")
            for item in summary["failed"]:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ✗ ID: {item['id']:2d} | {item['name']:<24} | Stage: {item['stage']} | Error: {item['error']}"
                    )
                )

        self.stdout.write("=" * 80)
