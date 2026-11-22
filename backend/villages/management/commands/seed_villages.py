from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from villages.models import Village


class Command(BaseCommand):
    help = "Seed pilot villages across Rajasthan agro-climatic monitoring zones (idempotent)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Rajasthan pilot monitoring villages..."))

        # Pilot villages with verified geographic coordinates (EPSG:4326: Longitude, Latitude)
        # Note: Administrative boundaries are explicitly set to None (omitted) rather than fabricated.
        pilot_villages = [
            {
                "name": "Piplantri",
                "district": "Rajsamand",
                "state": "Rajasthan",
                "longitude": 73.8347,
                "latitude": 25.0743,
                "area_hectares": 1050.0,   # Approximate revenue area
                "population": 5120,        # Approximate census estimate
                "notes": "Global model eco-village for watershed conservation and community afforestation",
            },
            {
                "name": "Kothariya",
                "district": "Rajsamand",
                "state": "Rajasthan",
                "longitude": 73.8567,
                "latitude": 24.9667,
                "area_hectares": 1420.0,   # Approximate revenue area
                "population": 4230,        # Approximate census estimate
                "notes": "Semi-arid agricultural belt monitored for soil erosion and aquifer recharge",
            },
            {
                "name": "Mandawa",
                "district": "Jhunjhunu",
                "state": "Rajasthan",
                "longitude": 75.1432,
                "latitude": 28.0553,
                "area_hectares": 2100.0,   # Approximate revenue area
                "population": 6500,        # Approximate census estimate
                "notes": "Shekhawati semi-arid zone monitored for groundwater drawdown and crop stress",
            },
            {
                "name": "Bhadla",
                "district": "Phalodi",
                "state": "Rajasthan",
                "longitude": 71.9167,
                "latitude": 27.5389,
                "area_hectares": 3500.0,   # Approximate revenue area
                "population": 1800,        # Approximate census estimate
                "notes": "Arid Thar desert periphery monitored for desertification and renewable energy land use",
            },
            {
                "name": "Kuldhara",
                "district": "Jaisalmer",
                "state": "Rajasthan",
                "longitude": 70.7833,
                "latitude": 26.8667,
                "area_hectares": 1800.0,   # Approximate heritage perimeter
                "population": None,        # Uninhabited heritage site (no population)
                "notes": "Hyper-arid Western Rajasthan historical rainwater harvesting reference site",
            },
        ]

        created_count = 0
        updated_count = 0

        for item in pilot_villages:
            location_point = Point(item["longitude"], item["latitude"], srid=4326)
            village, created = Village.objects.update_or_create(
                name=item["name"],
                district=item["district"],
                state=item["state"],
                defaults={
                    "location": location_point,
                    "boundary": None,  # Kept null - boundaries will be ingested via satellite GIS polygons
                    "area_hectares": item["area_hectares"],
                    "population": item["population"],
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  [+] Created: {village.name} ({village.district}) @ [{item['longitude']}, {item['latitude']}]"
                ))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(
                    f"  [*] Updated: {village.name} ({village.district}) @ [{item['longitude']}, {item['latitude']}]"
                ))

        self.stdout.write(self.style.SUCCESS(
            f"\nSeeding complete! {created_count} created, {updated_count} updated. Total villages: {Village.objects.count()}"
        ))

