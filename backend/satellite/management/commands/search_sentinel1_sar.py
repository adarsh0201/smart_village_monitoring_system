"""
Django Management Command: search_sentinel1_sar

Discovers Sentinel-1 C-band SAR radar imagery for target pilot villages
via Microsoft Planetary Computer and AWS STAC APIs.
"""

from django.core.management.base import BaseCommand, CommandError
from villages.models import Village
from satellite.services.sar_search import search_sentinel1_sar_scenes


class Command(BaseCommand):
    help = "Search Sentinel-1 C-band SAR scenes for pilot villages"

    def add_arguments(self, parser):
        parser.add_argument(
            "--village",
            type=str,
            default="Piplantri",
            help="Name of the village to search (default: Piplantri)"
        )
        parser.add_argument(
            "--start-date",
            type=str,
            default=None,
            help="Start date YYYY-MM-DD"
        )
        parser.add_argument(
            "--end-date",
            type=str,
            default=None,
            help="End date YYYY-MM-DD"
        )
        parser.add_argument(
            "--orbit",
            type=str,
            choices=["ascending", "descending", "any"],
            default="any",
            help="Satellite orbit direction"
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Maximum scenes to discover"
        )

    def handle(self, *args, **options):
        village_name = options["village"]
        start_date = options["start_date"]
        end_date = options["end_date"]
        orbit = None if options["orbit"] == "any" else options["orbit"]
        limit = options["limit"]

        village = Village.objects.filter(name__iexact=village_name).first()
        if not village:
            raise CommandError(f"Village '{village_name}' not found in database.")

        self.stdout.write(f"Searching Sentinel-1 SAR imagery for '{village.name}'...")
        scenes = search_sentinel1_sar_scenes(
            village=village,
            start_date=start_date,
            end_date=end_date,
            orbit_direction=orbit,
            limit=limit
        )

        if not scenes:
            self.stdout.write(self.style.WARNING("No Sentinel-1 scenes found matching criteria."))
            return

        self.stdout.write("=" * 85)
        self.stdout.write(f"{'SCENE ID':<35} | {'ACQUISITION (UTC)':<20} | {'ORBIT':<10} | {'POLARIZATIONS'}")
        self.stdout.write("=" * 85)
        for s in scenes:
            self.stdout.write(
                f"{s['scene_id'][:35]:<35} | "
                f"{str(s['acquisition_date'])[:19]:<20} | "
                f"{s['orbit_state']:<10} | "
                f"{', '.join(s['polarizations'])}"
            )
        self.stdout.write("=" * 85)
        self.stdout.write(self.style.SUCCESS(f"Found {len(scenes)} Sentinel-1 SAR scene(s)."))

