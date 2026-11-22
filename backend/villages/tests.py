from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.gis.geos import Point, MultiPolygon, Polygon
from .models import Village


class VillageModelTests(APITestCase):
    """
    Test suite for Village GeoDjango spatial model.
    """
    def setUp(self):
        self.village = Village.objects.create(
            name="Piplantri",
            district="Rajsamand",
            state="Rajasthan",
            location=Point(73.8347, 25.0743, srid=4326),
            area_hectares=1050.0,
            population=5120
        )

    def test_village_str(self):
        self.assertEqual(str(self.village), "Piplantri (Rajsamand, Rajasthan)")

    def test_latitude_longitude_properties(self):
        self.assertAlmostEqual(self.village.latitude, 25.0743, places=4)
        self.assertAlmostEqual(self.village.longitude, 73.8347, places=4)


class VillageAPITests(APITestCase):
    """
    Test suite for Village REST API endpoints.
    """
    def setUp(self):
        self.village = Village.objects.create(
            name="Kothariya",
            district="Rajsamand",
            state="Rajasthan",
            location=Point(73.8567, 24.9667, srid=4326),
            area_hectares=1420.0,
            population=4230
        )
        self.list_url = reverse('village-list-create')
        self.detail_url = reverse('village-detail', kwargs={'pk': self.village.pk})
        self.home_url = reverse('api-home')

    def test_api_home_endpoint(self):
        """Verify GET /api/ returns health and monitoring status."""
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("status"), "Running")
        self.assertIn("monitored_villages_count", response.data)

    def test_get_village_list(self):
        """Verify GET /api/villages/ returns village array with spatial information."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

        village_data = next((v for v in response.data if v['id'] == self.village.pk), None)
        self.assertIsNotNone(village_data)
        self.assertEqual(village_data['name'], "Kothariya")
        self.assertEqual(village_data['district'], "Rajsamand")
        self.assertAlmostEqual(village_data['latitude'], 24.9667, places=4)
        self.assertAlmostEqual(village_data['longitude'], 73.8567, places=4)
        self.assertEqual(village_data['location']['type'], "Point")
        self.assertAlmostEqual(village_data['location']['coordinates'][0], 73.8567, places=4)
        self.assertAlmostEqual(village_data['location']['coordinates'][1], 24.9667, places=4)

    def test_get_single_village(self):
        """Verify GET /api/villages/<id>/ returns single village details."""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.village.pk)
        self.assertEqual(response.data['name'], "Kothariya")

    def test_create_village_with_coordinates(self):
        """Verify POST /api/villages/ creates record from lat/lng."""
        payload = {
            "name": "Mandawa Test",
            "district": "Jhunjhunu",
            "state": "Rajasthan",
            "latitude": 28.0553,
            "longitude": 75.1432,
            "area_hectares": 2100.0,
            "population": 6500
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "Mandawa Test")
        self.assertAlmostEqual(response.data['latitude'], 28.0553, places=4)
        self.assertAlmostEqual(response.data['longitude'], 75.1432, places=4)

        # Confirm persisted in PostGIS database
        saved = Village.objects.get(pk=response.data['id'])
        self.assertAlmostEqual(saved.location.y, 28.0553, places=4)
        self.assertAlmostEqual(saved.location.x, 75.1432, places=4)

    def test_create_village_with_geojson_location(self):
        """Verify POST /api/villages/ accepts GeoJSON Point format."""
        payload = {
            "name": "Bhadla Test",
            "district": "Phalodi",
            "state": "Rajasthan",
            "location": {
                "type": "Point",
                "coordinates": [71.9167, 27.5389]
            },
            "area_hectares": 3500.0,
            "population": 1800
        }
        response = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertAlmostEqual(response.data['latitude'], 27.5389, places=4)
        self.assertAlmostEqual(response.data['longitude'], 71.9167, places=4)

    def test_reject_invalid_coordinates(self):
        """Verify POST /api/villages/ rejects invalid coordinate ranges."""
        # Invalid Latitude > 90
        payload_bad_lat = {
            "name": "Invalid Lat Village",
            "district": "Jaipur",
            "latitude": 95.0,
            "longitude": 75.0
        }
        response = self.client.post(self.list_url, payload_bad_lat, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid Longitude > 180
        payload_bad_lng = {
            "name": "Invalid Lng Village",
            "district": "Jaipur",
            "latitude": 26.0,
            "longitude": 195.0
        }
        response = self.client.post(self.list_url, payload_bad_lng, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_village(self):
        """Verify PUT /api/villages/<id>/ updates an existing village."""
        update_data = {
            "name": "Kothariya Eco-Zone",
            "district": "Rajsamand",
            "state": "Rajasthan",
            "latitude": 24.9700,
            "longitude": 73.8600,
            "area_hectares": 1450.0,
            "population": 4300
        }
        response = self.client.put(self.detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Kothariya Eco-Zone")
        self.assertAlmostEqual(response.data['latitude'], 24.9700, places=4)

    def test_delete_village(self):
        """Verify DELETE /api/villages/<id>/ removes the village record."""
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Village.objects.filter(pk=self.village.pk).exists())
