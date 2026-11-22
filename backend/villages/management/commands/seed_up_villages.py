"""
Django Management Command: seed_up_villages

Seeds the 15 pilot monitoring villages from Uttar Pradesh into PostgreSQL/PostGIS.
Covers Ghazipur, Etawah, Lucknow, Gorakhpur, Deoria, and Barabanki.

Every record includes:
- Exact Village Name
- Accurate District Name (to filter state-wide datasets and prevent spatial false positives)
- State: 'Uttar Pradesh'
- Verified Coordinates (EPSG:4326: Lon, Lat)
- Area & Population estimates
- Remote sensing monitoring notes

Idempotent: Uses update_or_create to prevent duplicate entries.
"""

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from villages.models import Village

UP_PILOT_VILLAGES = [
    {
        "name": "Gahmar",
        "district": "Ghazipur",
        "state": "Uttar Pradesh",
        "longitude": 83.80838,
        "latitude": 25.49801,
        "area_hectares": 3450.0,
        "population": 25994,
        "notes": "Historic Ganga riverbank village, one of the largest villages in India; intensive alluvial agriculture and flood monitoring",
    },
    {
        "name": "Saifai",
        "district": "Etawah",
        "state": "Uttar Pradesh",
        "longitude": 78.96255,
        "latitude": 26.95911,
        "area_hectares": 1250.0,
        "population": 7141,
        "notes": "Canal-irrigated central Doab agrarian hub with developed infrastructure; agricultural land-use monitoring",
    },
    {
        "name": "Juggaur",
        "district": "Lucknow",
        "state": "Uttar Pradesh",
        "longitude": 81.08373,
        "latitude": 26.87307,
        "area_hectares": 820.0,
        "population": 6200,
        "notes": "Chinhat peri-urban agrarian-wetland corridor in Lucknow; monitored for urban expansion and water body conservation",
    },
    {
        "name": "Itaunja",
        "district": "Lucknow",
        "state": "Uttar Pradesh",
        "longitude": 80.90218,
        "latitude": 27.08300,
        "area_hectares": 950.0,
        "population": 7800,
        "notes": "Northern Lucknow Gomti basin agricultural belt; intensive horticulture and mango belt monitoring",
    },
    {
        "name": "Dumri Khas",
        "district": "Gorakhpur",
        "state": "Uttar Pradesh",
        "longitude": 83.14352,
        "latitude": 26.85509,
        "area_hectares": 780.0,
        "population": 5400,
        "notes": "Rapti river basin agricultural tract; seasonal waterlogging and paddy cultivation monitoring",
    },
    {
        "name": "Bhatkaon",
        "district": "Gorakhpur",
        "state": "Uttar Pradesh",
        "longitude": 83.46495,
        "latitude": 26.41787,
        "area_hectares": 620.0,
        "population": 4300,
        "notes": "Southern Gorakhpur agrarian belt; monitored for seasonal drainage, sugarcane crops, and groundwater recharge",
    },
    {
        "name": "Chainpur",
        "district": "Deoria",
        "state": "Uttar Pradesh",
        "longitude": 83.75289,
        "latitude": 26.68885,
        "area_hectares": 580.0,
        "population": 3900,
        "notes": "Eastern Terai fringe in Deoria; high-density sugarcane and paddy rotation tract",
    },
    {
        "name": "Sonbarsa",
        "district": "Deoria",
        "state": "Uttar Pradesh",
        "longitude": 83.58766,
        "latitude": 26.40963,
        "area_hectares": 650.0,
        "population": 4600,
        "notes": "Ghaghra floodplain agricultural belt in southern Deoria; siltation and soil moisture monitoring",
    },
    {
        "name": "Atirajpur",
        "district": "Etawah",
        "state": "Uttar Pradesh",
        "longitude": 78.97264,
        "latitude": 26.97089,
        "area_hectares": 480.0,
        "population": 2800,
        "notes": "Etawah Doab agricultural tract; wheat and mustard crop canopy and canal irrigation monitoring",
    },
    {
        "name": "Baidpura",
        "district": "Etawah",
        "state": "Uttar Pradesh",
        "longitude": 78.99396,
        "latitude": 26.86807,
        "area_hectares": 690.0,
        "population": 4200,
        "notes": "Central Etawah semi-arid Doab belt; groundwater drawdown and pulse cultivation monitoring",
    },
    {
        "name": "Parasana",
        "district": "Etawah",
        "state": "Uttar Pradesh",
        "longitude": 79.09894,
        "latitude": 26.97240,
        "area_hectares": 520.0,
        "population": 3100,
        "notes": "Etawah eastern agrarian perimeter; canal network water distribution and soil salinity monitoring",
    },
    {
        "name": "Phoolpur",
        "district": "Etawah",
        "state": "Uttar Pradesh",
        "longitude": 79.01461,
        "latitude": 26.84605,
        "area_hectares": 440.0,
        "population": 2600,
        "notes": "Sengur river catchment zone in southern Etawah; ravines and soil erosion monitoring",
    },
    {
        "name": "Tulsipur",
        "district": "Etawah",
        "state": "Uttar Pradesh",
        "longitude": 79.05970,
        "latitude": 26.89497,
        "area_hectares": 510.0,
        "population": 3400,
        "notes": "Canal-fed agrarian village in Etawah; intensive seasonal cropping and vegetation vigor",
    },
    {
        "name": "Ujhiyani",
        "district": "Etawah",
        "state": "Uttar Pradesh",
        "longitude": 78.99073,
        "latitude": 26.95198,
        "area_hectares": 610.0,
        "population": 3700,
        "notes": "Etawah northwest agricultural tract; multi-crop seasonal rotations and crop residue monitoring",
    },
    {
        "name": "Haswapara",
        "district": "Barabanki",
        "state": "Uttar Pradesh",
        "longitude": 81.07401,
        "latitude": 27.19860,
        "area_hectares": 470.0,
        "population": 2950,
        "notes": "Barabanki Gomti-Kalyani interfluve; mentha, pulse, and cereal multi-tier farming monitoring",
    },
]


class Command(BaseCommand):
    help = "Seed the 15 pilot monitoring villages from Uttar Pradesh with accurate district names"

    def add_arguments(self, parser):
        parser.add_argument(
            "--generate-provisional-buffers",
            action="store_true",
            help="Generate 1.5 km provisional polygonal buffers so villages render immediately on GIS map before shapefile is loaded"
        )
        parser.add_argument(
            "--clean-old-up",
            action="store_true",
            help="Clean previous experimental UP records before seeding the 15 user-selected villages"
        )

    def handle(self, *args, **options):
        gen_buffers = options["generate_provisional_buffers"]
        clean_old = options["clean_old_up"]

        self.stdout.write("=" * 80)
        self.stdout.write("SEEDING 15 PILOT MONITORING VILLAGES ACROSS UTTAR PRADESH")
        self.stdout.write("=" * 80)

        target_names = [v["name"] for v in UP_PILOT_VILLAGES]

        if clean_old:
            deleted_count, _ = Village.objects.filter(state="Uttar Pradesh").exclude(name__in=target_names).delete()
            if deleted_count > 0:
                self.stdout.write(self.style.WARNING(f"Cleaned {deleted_count} previous non-target UP village record(s)."))

        created_count = 0
        updated_count = 0

        for item in UP_PILOT_VILLAGES:
            lon = item["longitude"]
            lat = item["latitude"]
            location_point = Point(lon, lat, srid=4326)

            boundary_geom = None
            if gen_buffers:
                from villages.management.commands.fallback_geometries import generate_polygonal_buffer
                # UTM 43N for Western UP (< 78°E), UTM 44N for Central/Eastern UP (>= 78°E)
                utm_epsg = 32643 if lon < 78.0 else 32644
                boundary_geom, calc_area = generate_polygonal_buffer(
                    lon=lon,
                    lat=lat,
                    radius_km=1.5,
                    num_sides=16,
                    utm_epsg=utm_epsg
                )
                item["area_hectares"] = calc_area

            defaults = {
                "location": location_point,
                "area_hectares": item["area_hectares"],
                "population": item["population"],
            }
            if boundary_geom:
                defaults["boundary"] = boundary_geom

            village, created = Village.objects.update_or_create(
                name=item["name"],
                district=item["district"],
                state=item["state"],
                defaults=defaults
            )

            status_symbol = "[+]" if created else "[*]"
            status_text = "Created" if created else "Updated"
            if created:
                created_count += 1
            else:
                updated_count += 1

            self.stdout.write(
                f"  {status_symbol} {status_text}: {village.name:<15} | District: {village.district:<12} | [{lon:.5f}, {lat:.5f}]"
            )

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(
            f"Seeding complete! {created_count} created, {updated_count} updated.\n"
            f"Total UP villages: {Village.objects.filter(state='Uttar Pradesh').count()} | Total DB villages: {Village.objects.count()}"
        ))
        self.stdout.write("=" * 80)
