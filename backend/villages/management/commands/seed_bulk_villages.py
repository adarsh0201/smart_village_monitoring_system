"""
Django Management Command: seed_bulk_villages

Reads a CSV file containing columns for Village Name, District Name, State Name,
and optional coordinates/demographics, and bulk-creates or updates records in PostgreSQL/PostGIS.

Supports flexible CSV column headers:
  - Village: 'village', 'village_name', 'name', 'village name'
  - District: 'district', 'district_name', 'district name'
  - State: 'state', 'state_name', 'state name'
  - Coordinates (Optional): 'latitude'/'lat', 'longitude'/'lon'/'lng'
  - Attributes (Optional): 'population'/'pop', 'area_hectares'/'area'/'area_ha'

If latitude/longitude are omitted in the CSV, representative district centroid
coordinates are automatically assigned so records immediately satisfy PostGIS
PointField requirements before load_village_shapefile extracts exact boundary centroids.
"""

import os
import csv
import logging
from django.core.management.base import BaseCommand, CommandError
from django.contrib.gis.geos import Point
from django.db import transaction
from villages.models import Village

logger = logging.getLogger(__name__)

# Approximate district centroids [Longitude, Latitude] for automatic coordinate fallback
DISTRICT_CENTROIDS = {
    # Uttar Pradesh Districts
    "agra": (78.0081, 27.1767), "aligarh": (78.0880, 27.8974), "allahabad": (81.8463, 25.4358),
    "ambedkar nagar": (82.6800, 26.4400), "amethi": (81.8100, 26.1500), "amroha": (78.4700, 28.9000),
    "auraiya": (79.5100, 26.4600), "ayodhya": (82.1330, 26.6020), "azamgarh": (83.1900, 26.0700),
    "baghpat": (77.2200, 28.9400), "bahraich": (81.5900, 27.5700), "ballia": (84.1500, 25.7600),
    "balrampur": (82.1800, 27.4300), "banda": (80.3300, 25.4800), "barabanki": (81.1900, 26.9200),
    "bareilly": (79.4300, 28.3600), "basti": (82.7600, 26.8000), "bhadohi": (82.5700, 25.3900),
    "bijnor": (78.1300, 29.3700), "budaun": (79.1200, 28.0300), "bulandshahr": (77.8500, 28.4000),
    "chandauli": (83.2700, 25.2600), "chitrakoot": (80.8700, 25.2100), "deoria": (83.7800, 26.5000),
    "etah": (78.6600, 27.5600), "etawah": (79.0200, 26.7700), "faizabad": (82.1330, 26.6020),
    "farrukhabad": (79.5700, 27.3800), "fatehpur": (80.8100, 25.9300), "firozabad": (78.4000, 27.1500),
    "gautam buddha nagar": (77.5000, 28.3500), "ghaziabad": (77.4500, 28.6700), "ghazipur": (83.5800, 25.5800),
    "gonda": (81.9600, 27.1300), "gorakhpur": (83.3700, 26.7600), "hamirpur": (80.1500, 25.9500),
    "hapur": (77.7800, 28.7300), "hardoi": (80.1200, 27.3900), "hathras": (78.0500, 27.6000),
    "jalaun": (79.3300, 26.1500), "jaunpur": (82.6800, 25.7500), "jhansi": (78.5700, 25.4500),
    "kannauj": (79.9200, 27.0500), "kanpur dehat": (79.9500, 26.3500), "kanpur nagar": (80.3300, 26.4500),
    "kasganj": (78.6500, 27.8100), "kaushambi": (81.4000, 25.5300), "kheri": (80.7800, 27.9400),
    "kushinagar": (83.8900, 26.9000), "lakhimpur kheri": (80.7800, 27.9400), "lalitpur": (78.4200, 24.6900),
    "lucknow": (80.9462, 26.8467), "maharajganj": (83.5600, 27.1500), "mahoba": (79.8700, 25.2900),
    "mainpuri": (79.0300, 27.2300), "mathura": (77.6700, 27.4900), "mau": (83.5600, 26.0000),
    "meerut": (77.7000, 28.9800), "mirzapur": (82.5600, 25.1500), "moradabad": (78.7800, 28.8300),
    "muzaffarnagar": (77.7000, 29.4700), "pilibhit": (79.8000, 28.6300), "pratapgarh": (81.9800, 25.9000),
    "prayagraj": (81.8463, 25.4358), "raebareli": (81.2400, 26.2200), "rampur": (79.0200, 28.8100),
    "saharanpur": (77.5400, 29.9600), "sambhal": (78.5700, 28.5800), "sant kabir nagar": (83.0500, 26.7800),
    "shahjahanpur": (79.9100, 27.8800), "shamli": (77.3000, 29.4500), "shrawasti": (81.9500, 27.7000),
    "siddharthnagar": (82.7800, 27.2700), "sitapur": (80.6800, 27.5600), "sonbhadra": (83.0700, 24.6900),
    "sultanpur": (82.0700, 26.2600), "unnao": (80.4900, 26.5400), "varanasi": (82.9739, 25.3176),

    # Rajasthan Districts
    "ajmer": (74.6400, 26.4500), "alwar": (76.6000, 27.5600), "banswara": (74.4400, 23.5500),
    "baran": (76.5100, 25.1000), "barmer": (71.3900, 25.7500), "bharatpur": (77.4900, 27.2200),
    "bhilwara": (74.6400, 25.3500), "bikaner": (73.3100, 28.0200), "bundi": (75.6400, 25.4400),
    "chittorgarh": (74.6300, 24.8900), "churu": (74.9600, 28.2900), "dausa": (76.3400, 26.8900),
    "dholpur": (77.8900, 26.7000), "dungarpur": (73.7100, 23.8400), "hanumangarh": (74.3200, 29.5800),
    "jaipur": (75.7873, 26.9124), "jaisalmer": (70.9200, 26.9100), "jalore": (72.6100, 25.3400),
    "jhalawar": (76.1600, 24.6000), "jhunjhunu": (75.3900, 28.1300), "jodhpur": (73.0200, 26.2800),
    "karauli": (77.0200, 26.5000), "kota": (75.8400, 25.1800), "nagaur": (73.7400, 27.2000),
    "pali": (73.3200, 25.7700), "phalodi": (72.3600, 27.1300), "pratapgarh_rj": (74.7800, 24.0300),
    "rajsamand": (73.8800, 25.0700), "sawai madhopur": (76.3800, 26.0000), "sikar": (75.1400, 27.6100),
    "sirohi": (72.8600, 24.8800), "sri ganganagar": (73.8800, 29.9200), "tonk": (75.7900, 26.1600),
    "udaipur": (73.7125, 24.5854)
}


class Command(BaseCommand):
    help = "Bulk-seed villages into the database from a CSV file (Village Name, District, State)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", "-f",
            type=str,
            required=True,
            help="Path to the CSV file (e.g., data/villages.csv)"
        )
        parser.add_argument(
            "--default-state",
            type=str,
            default="Uttar Pradesh",
            help="Default state name if omitted in CSV row (default: 'Uttar Pradesh')"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate CSV rows and print parsed data without committing to database"
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            default=True,
            help="Update existing records matching (name, district, state) (default: True)"
        )

    def _normalize_header(self, header):
        """Normalize CSV column header to lowercase alphanumeric."""
        return header.strip().lower().replace(" ", "_").replace("-", "_")

    def _find_column(self, normalized_headers, candidate_keys):
        """Find the matching column index from candidate names."""
        for cand in candidate_keys:
            if cand in normalized_headers:
                return normalized_headers.index(cand)
        return None

    def handle(self, *args, **options):
        csv_path = options["file"]
        default_state = options["default_state"]
        dry_run = options["dry_run"]
        update_existing = options["update_existing"]

        if not os.path.exists(csv_path):
            raise CommandError(f"CSV file not found at path: {csv_path}")

        self.stdout.write("=" * 80)
        self.stdout.write(f"BULK VILLAGE SEEDER: {csv_path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("Mode: DRY RUN (No changes will be saved to database)"))
        self.stdout.write("=" * 80)

        rows_to_process = []
        with open(csv_path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            raw_headers = next(reader, None)
            if not raw_headers:
                raise CommandError("The CSV file is empty or missing headers.")

            norm_headers = [self._normalize_header(h) for h in raw_headers]

            # Identify column positions
            idx_name = self._find_column(norm_headers, ["village_name", "village", "name", "v_name", "vill_name"])
            idx_district = self._find_column(norm_headers, ["district_name", "district", "dist_name", "dist"])
            idx_state = self._find_column(norm_headers, ["state_name", "state", "st_name", "st"])
            idx_lat = self._find_column(norm_headers, ["latitude", "lat", "y"])
            idx_lon = self._find_column(norm_headers, ["longitude", "lon", "lng", "long", "x"])
            idx_pop = self._find_column(norm_headers, ["population", "pop", "census_pop"])
            idx_area = self._find_column(norm_headers, ["area_hectares", "area", "area_ha", "hectares"])

            if idx_name is None:
                raise CommandError("CSV must contain a 'Village Name' or 'Village' column.")
            if idx_district is None:
                raise CommandError("CSV must contain a 'District Name' or 'District' column.")

            line_no = 1
            for row in reader:
                line_no += 1
                if not row or all(not cell.strip() for cell in row):
                    continue

                v_name = row[idx_name].strip()
                v_dist = row[idx_district].strip()
                if not v_name or not v_dist:
                    self.stdout.write(self.style.WARNING(f"  Line {line_no}: Missing name or district. Skipping."))
                    continue

                v_state = row[idx_state].strip() if (idx_state is not None and len(row) > idx_state and row[idx_state].strip()) else default_state

                # Parse optional coordinates
                v_lat, v_lon = None, None
                if idx_lat is not None and len(row) > idx_lat and row[idx_lat].strip():
                    try:
                        v_lat = float(row[idx_lat].strip())
                    except ValueError:
                        pass
                if idx_lon is not None and len(row) > idx_lon and row[idx_lon].strip():
                    try:
                        v_lon = float(row[idx_lon].strip())
                    except ValueError:
                        pass

                # Fallback to district centroid if coordinates omitted
                coord_source = "CSV"
                if v_lat is None or v_lon is None:
                    dist_key = v_dist.lower()
                    if dist_key in DISTRICT_CENTROIDS:
                        v_lon, v_lat = DISTRICT_CENTROIDS[dist_key]
                        coord_source = "District Centroid (Fallback)"
                    else:
                        # General state fallback
                        v_lon, v_lat = (80.9462, 26.8467) if "uttar" in v_state.lower() else (75.7873, 26.9124)
                        coord_source = "State Centroid (Fallback)"

                # Parse optional population and area
                v_pop = None
                if idx_pop is not None and len(row) > idx_pop and row[idx_pop].strip():
                    try:
                        v_pop = int(float(row[idx_pop].strip()))
                    except ValueError:
                        pass

                v_area = None
                if idx_area is not None and len(row) > idx_area and row[idx_area].strip():
                    try:
                        v_area = float(row[idx_area].strip())
                    except ValueError:
                        pass

                rows_to_process.append({
                    "name": v_name,
                    "district": v_dist,
                    "state": v_state,
                    "lon": v_lon,
                    "lat": v_lat,
                    "coord_source": coord_source,
                    "population": v_pop,
                    "area_hectares": v_area,
                    "line": line_no
                })

        self.stdout.write(f"Parsed {len(rows_to_process)} village records from CSV.\n")

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for item in rows_to_process:
                loc_point = Point(item["lon"], item["lat"], srid=4326)

                defaults = {
                    "location": loc_point,
                }
                if item["population"] is not None:
                    defaults["population"] = item["population"]
                if item["area_hectares"] is not None:
                    defaults["area_hectares"] = item["area_hectares"]

                if dry_run:
                    self.stdout.write(
                        f"  [DRY-RUN] {item['name']:<18} | Dist: {item['district']:<14} | "
                        f"State: {item['state']:<14} | [{item['lon']:.4f}, {item['lat']:.4f}] ({item['coord_source']})"
                    )
                    continue

                village, created = Village.objects.update_or_create(
                    name=item["name"],
                    district=item["district"],
                    state=item["state"],
                    defaults=defaults
                )

                sym = "[+]" if created else "[*]"
                tag = "Created" if created else "Updated"
                if created:
                    created_count += 1
                else:
                    updated_count += 1

                self.stdout.write(
                    f"  {sym} {tag}: {village.name:<18} | Dist: {village.district:<14} | "
                    f"[{item['lon']:.4f}, {item['lat']:.4f}] ({item['coord_source']})"
                )

            if dry_run:
                self.stdout.write("\n" + self.style.WARNING("DRY RUN COMPLETE: No database transactions were committed."))
                return

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(
            f"Bulk Seeding Complete!\n"
            f"Created: {created_count} | Updated: {updated_count} | Total Processed: {len(rows_to_process)}\n"
            f"Total Villages in Database: {Village.objects.count()}"
        ))
        self.stdout.write("=" * 80)
