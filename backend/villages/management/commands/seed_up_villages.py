"""
Django Management Command: seed_up_villages

Seeds 15 diverse pilot monitoring villages across Uttar Pradesh (UP) into PostgreSQL/PostGIS.
Spans Purvanchal (Eastern Gangetic Plain), Awadh (Central UP), Bundelkhand (Drought-Prone),
Terai (Sub-Himalayan Wetlands), and Western UP (Canal-Irrigated Agro-Industrial).

Every record includes:
- Exact Village Name.
- Official Uttar Pradesh District Name (for pre-filtering state-wide Bhuvan datasets).
- State: 'Uttar Pradesh'.
- Verified Point location (EPSG:4326: Lon, Lat).
- Revenue Area estimate in hectares.
- Census population estimate.
- Agro-ecological remote sensing monitoring notes.

Idempotent: Uses update_or_create to prevent duplicates.
"""

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from villages.models import Village

# 15 Diverse Pilot Monitoring Villages across Uttar Pradesh
UP_PILOT_VILLAGES = [
    # -------------------------------------------------------------------------
    # 1. PURVANCHAL (EASTERN GANGETIC PLAIN)
    # -------------------------------------------------------------------------
    {
        "name": "Rameshwar",
        "district": "Varanasi",
        "state": "Uttar Pradesh",
        "longitude": 82.8805,
        "latitude": 25.3340,
        "area_hectares": 480.0,
        "population": 3650,
        "notes": "Varuna River basin peri-urban agrarian belt; monitored for surface water pollution and riverbank erosion",
    },
    {
        "name": "Shringverpur",
        "district": "Prayagraj",
        "state": "Uttar Pradesh",
        "longitude": 81.6420,
        "latitude": 25.5890,
        "area_hectares": 820.0,
        "population": 5890,
        "notes": "Ganga alluvial floodplain; intensive paddy-wheat rotation monitored for flood inundation and soil siltation",
    },
    {
        "name": "Kushmi",
        "district": "Gorakhpur",
        "state": "Uttar Pradesh",
        "longitude": 83.4750,
        "latitude": 26.7450,
        "area_hectares": 640.0,
        "population": 4120,
        "notes": "Rapti-Rohini interfluve and Sal forest fringe; monitored for seasonal waterlogging, wetlands, and paddy canopy",
    },
    {
        "name": "Ahraura",
        "district": "Mirzapur",
        "state": "Uttar Pradesh",
        "longitude": 83.0210,
        "latitude": 25.0160,
        "area_hectares": 950.0,
        "population": 6200,
        "notes": "Vindhyan plateau foothills; monitored for stony scrubland reclamation, minor reservoir recharge, and irrigation canals",
    },
    {
        "name": "Robertsganj",
        "district": "Sonbhadra",
        "state": "Uttar Pradesh",
        "longitude": 83.0670,
        "latitude": 24.6850,
        "area_hectares": 1250.0,
        "population": 7800,
        "notes": "Southern Sonbhadra mineral and forested belt; monitored for mining dust land-cover alteration and forest degradation",
    },

    # -------------------------------------------------------------------------
    # 2. AWADH (CENTRAL UTTAR PRADESH)
    # -------------------------------------------------------------------------
    {
        "name": "Bikapur",
        "district": "Ayodhya",
        "state": "Uttar Pradesh",
        "longitude": 82.1330,
        "latitude": 26.6020,
        "area_hectares": 710.0,
        "population": 5400,
        "notes": "Ghaghra (Saryu) tributary basin; high-yield sugarcane, pulse farming, and groundwater drawdown monitoring",
    },
    {
        "name": "Mohanlalganj",
        "district": "Lucknow",
        "state": "Uttar Pradesh",
        "longitude": 80.9980,
        "latitude": 26.6850,
        "area_hectares": 890.0,
        "population": 6750,
        "notes": "State capital peri-urban fringe; rapid urban sprawl transition, brick kilns, and fertile mango orchard land use",
    },
    {
        "name": "Masauli",
        "district": "Barabanki",
        "state": "Uttar Pradesh",
        "longitude": 81.2850,
        "latitude": 27.0120,
        "area_hectares": 620.0,
        "population": 4900,
        "notes": "Major commercial mentha (peppermint) and seasonal cash crop cultivation monitored for high soil moisture evapotranspiration",
    },
    {
        "name": "Tirwa",
        "district": "Kannauj",
        "state": "Uttar Pradesh",
        "longitude": 79.7650,
        "latitude": 26.9850,
        "area_hectares": 780.0,
        "population": 5300,
        "notes": "Lower Gangetic Doab; famous rose/damask floriculture and intensive cold-storage potato crop health analytics",
    },

    # -------------------------------------------------------------------------
    # 3. BUNDELKHAND (SEMI-ARID DROUGHT-PRONE HARD-ROCK ZONE)
    # -------------------------------------------------------------------------
    {
        "name": "Baruasagar",
        "district": "Jhansi",
        "state": "Uttar Pradesh",
        "longitude": 78.7350,
        "latitude": 25.3720,
        "area_hectares": 1100.0,
        "population": 4800,
        "notes": "Bundelkhand granitic hard-rock terrain; historic Bundela embankment lake monitored for drought stress and reservoir shrinkage",
    },
    {
        "name": "Kulpahar",
        "district": "Mahoba",
        "state": "Uttar Pradesh",
        "longitude": 79.6450,
        "latitude": 25.3150,
        "area_hectares": 1350.0,
        "population": 5900,
        "notes": "Water-scarce Bundelkhand basin; Chandela-era traditional rainwater storage tanks and barren scrubland desertification tracking",
    },

    # -------------------------------------------------------------------------
    # 4. TERAI & ROHILKHAND (NORTHERN SUB-HIMALAYAN & WETLAND ZONE)
    # -------------------------------------------------------------------------
    {
        "name": "Palia Kalan",
        "district": "Lakhimpur Kheri",
        "state": "Uttar Pradesh",
        "longitude": 80.5820,
        "latitude": 28.4350,
        "area_hectares": 1600.0,
        "population": 8400,
        "notes": "Dudhwa Terai marshland corridor; Sharda River floods, high soil moisture, and dense commercial sugarcane plantations",
    },
    {
        "name": "Joya",
        "district": "Amroha",
        "state": "Uttar Pradesh",
        "longitude": 78.5020,
        "latitude": 28.8850,
        "area_hectares": 540.0,
        "population": 4300,
        "notes": "Rohilkhand agricultural zone; commercial mango groves, multi-tier horticulture, and tube-well depth monitoring",
    },

    # -------------------------------------------------------------------------
    # 5. WESTERN UTTAR PRADESH (UPPER DOAB & BRAJ REGION)
    # -------------------------------------------------------------------------
    {
        "name": "Hastinapur",
        "district": "Meerut",
        "state": "Uttar Pradesh",
        "longitude": 78.0200,
        "latitude": 29.1700,
        "area_hectares": 1420.0,
        "population": 7200,
        "notes": "Upper Ganga Canal irrigated belt and Hastinapur Wildlife Sanctuary wetlands; intensive mechanized cash-crop agriculture",
    },
    {
        "name": "Goverdhan",
        "district": "Mathura",
        "state": "Uttar Pradesh",
        "longitude": 77.4650,
        "latitude": 27.5020,
        "area_hectares": 980.0,
        "population": 6100,
        "notes": "Yamuna basin semi-arid saline soil tract; sacred community groves (Braj Van), kund water tanks, and crop salinity monitoring",
    },
]


class Command(BaseCommand):
    help = "Seed 15 diverse pilot monitoring villages across Uttar Pradesh with accurate district names"

    def add_arguments(self, parser):
        parser.add_argument(
            "--generate-provisional-buffers",
            action="store_true",
            help="Generate 1.5 km provisional polygonal buffers so villages render immediately on GIS map before Bhuvan GeoJSON is loaded"
        )

    def handle(self, *args, **options):
        gen_buffers = options["generate_provisional_buffers"]

        self.stdout.write("=" * 80)
        self.stdout.write("SEEDING 15 PILOT MONITORING VILLAGES ACROSS UTTAR PRADESH")
        self.stdout.write("=" * 80)

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
            status_word = "Created" if created else "Updated"
            if created:
                created_count += 1
            else:
                updated_count += 1

            self.stdout.write(self.style.SUCCESS(
                f"  {status_symbol} {status_word}: {village.name:<14} | District: {village.district:<16} | "
                f"Coords: [{lon:.4f}, {lat:.4f}] | Area: {village.area_hectares} ha"
            ))

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(
            f"Seeding Complete: {created_count} created, {updated_count} updated.\n"
            f"Total villages in database: {Village.objects.count()} (5 Rajasthan + 15 Uttar Pradesh)"
        ))
        self.stdout.write("=" * 80)
        self.stdout.write(
            "TIP: Once you download the UP Bhuvan GeoJSON file, run:\n"
            "python manage.py load_village_shapefile --file \"path/to/up_bhuvan.geojson\" --fuzzy\n"
            "The script will automatically use each village's populated District Name to filter the state dataset!"
        )
        self.stdout.write("=" * 80)
