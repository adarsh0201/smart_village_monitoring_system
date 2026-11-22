import numpy as np
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase
from django.contrib.gis.geos import Point
from django.utils import timezone

from villages.models import Village
from .models import SatelliteScene, SatelliteBand, SpectralIndex
from .services.aoi import generate_village_monitoring_aoi
from .services.indices import (
    calculate_ndvi,
    calculate_ndwi,
    calculate_savi,
    calculate_mndwi,
    calculate_index_statistics,
    resample_to_reference,
)
from rasterio.warp import Resampling
from affine import Affine


class SatellitePipelineTests(APITestCase):
    def setUp(self):
        self.village = Village.objects.create(
            name="Piplantri Pilot",
            district="Rajsamand",
            state="Rajasthan",
            location=Point(73.8347, 25.0743, srid=4326),
            area_hectares=1050.0,
            population=5120
        )
        self.scene = SatelliteScene.objects.create(
            village=self.village,
            provider="AWS Earth Search (Element 84)",
            collection="sentinel-2-l2a",
            scene_id="S2B_43RCH_20240322_0_L2A",
            acquisition_date=timezone.now(),
            cloud_cover=0.0,
            aoi_cloud_cover=0.0,
            processing_level="Level-2A",
            status="completed"
        )
        self.band_b02 = SatelliteBand.objects.create(
            scene=self.scene,
            band_name="B02",
            file_path="satellite/villages/1/S2B_43RCH_20240322_0_L2A/B02.tif",
            resolution=10.0,
            crs="EPSG:32643",
            width=505,
            height=496,
            file_size=375850
        )
        self.band_scl = SatelliteBand.objects.create(
            scene=self.scene,
            band_name="SCL",
            file_path="satellite/villages/1/S2B_43RCH_20240322_0_L2A/SCL.tif",
            resolution=20.0,
            crs="EPSG:32643",
            width=253,
            height=248,
            file_size=5494
        )

    def test_aoi_generation_provisional(self):
        aoi = generate_village_monitoring_aoi(self.village, buffer_km=2.5)
        self.assertTrue(aoi['is_provisional'])
        self.assertEqual(aoi['buffer_km'], 2.5)
        self.assertEqual(len(aoi['bbox']), 4)
        self.assertIn("Provisional monitoring AOI", aoi['description'])

    def test_satellite_scene_list(self):
        url = reverse('satellite-scene-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['scene_id'], "S2B_43RCH_20240322_0_L2A")

    def test_satellite_scene_detail(self):
        url = reverse('satellite-scene-detail', kwargs={'pk': self.scene.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['scene_id'], "S2B_43RCH_20240322_0_L2A")
        self.assertEqual(len(response.data['bands']), 2)

    def test_village_satellite_scenes(self):
        url = reverse('village-satellite-scenes', kwargs={'village_id': self.village.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_satellite_search_validation(self):
        url = reverse('satellite-search')
        # Missing village_id
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SpectralIndicesEngineUnitTests(TestCase):
    """
    Automated unit tests verifying mathematical correctness, reflectance scaling,
    cloud masking, resampling, NoData handling, division by zero, and stats.
    """
    def setUp(self):
        # Known synthetic float32 reflectance arrays (values in [0.0, 1.0])
        # Shape 2x2
        self.nir = np.array([[0.60, 0.10], [0.80, 0.00]], dtype=np.float32)
        self.red = np.array([[0.20, 0.10], [0.10, 0.00]], dtype=np.float32)
        self.green = np.array([[0.15, 0.40], [0.20, 0.05]], dtype=np.float32)
        self.swir = np.array([[0.10, 0.05], [0.30, 0.15]], dtype=np.float32)

    def test_ndvi_mathematical_correctness(self):
        # (0.6 - 0.2) / (0.6 + 0.2) = 0.4 / 0.8 = 0.50
        # (0.1 - 0.1) / (0.1 + 0.1) = 0.0
        # (0.8 - 0.1) / (0.8 + 0.1) = 0.7 / 0.9 = 0.7778
        # (0.0 - 0.0) / (0.0 + 0.0) -> division by zero -> np.nan
        ndvi = calculate_ndvi(self.nir, self.red)
        self.assertAlmostEqual(ndvi[0, 0], 0.50, places=4)
        self.assertAlmostEqual(ndvi[0, 1], 0.00, places=4)
        self.assertAlmostEqual(ndvi[1, 0], 0.7778, places=3)
        self.assertTrue(np.isnan(ndvi[1, 1]))

    def test_ndwi_mathematical_correctness(self):
        # (Green - NIR) / (Green + NIR)
        # (0.15 - 0.60) / (0.15 + 0.60) = -0.45 / 0.75 = -0.60 (vegetation)
        # (0.40 - 0.10) / (0.40 + 0.10) = 0.30 / 0.50 = +0.60 (water)
        ndwi = calculate_ndwi(self.green, self.nir)
        self.assertAlmostEqual(ndwi[0, 0], -0.60, places=4)
        self.assertAlmostEqual(ndwi[0, 1], 0.60, places=4)

    def test_savi_mathematical_correctness_and_scaling(self):
        # ((NIR - Red) / (NIR + Red + L)) * (1 + L) with L=0.5
        # ((0.6 - 0.2) / (0.6 + 0.2 + 0.5)) * 1.5 = (0.4 / 1.3) * 1.5 = 0.4615
        savi = calculate_savi(self.nir, self.red, L=0.5)
        self.assertAlmostEqual(savi[0, 0], 0.4615, places=3)

    def test_mndwi_mathematical_correctness(self):
        # (Green - SWIR) / (Green + SWIR)
        # (0.15 - 0.10) / (0.15 + 0.10) = 0.05 / 0.25 = 0.20
        # (0.40 - 0.05) / (0.40 + 0.05) = 0.35 / 0.45 = 0.7778 (water)
        mndwi = calculate_mndwi(self.green, self.swir)
        self.assertAlmostEqual(mndwi[0, 0], 0.20, places=4)
        self.assertAlmostEqual(mndwi[0, 1], 0.7778, places=3)

    def test_mask_application(self):
        # Mask out pixel (0, 0)
        mask = np.array([[True, False], [False, False]])
        ndvi = calculate_ndvi(self.nir, self.red, mask=mask)
        self.assertTrue(np.isnan(ndvi[0, 0]))
        self.assertFalse(np.isnan(ndvi[0, 1]))

    def test_division_by_zero_safety(self):
        # Array with complete zeros
        zeros = np.zeros((3, 3), dtype=np.float32)
        ndvi = calculate_ndvi(zeros, zeros)
        self.assertTrue(np.all(np.isnan(ndvi)))

    def test_index_statistics_calculation(self):
        # Test array with 3 valid values and 1 NaN
        arr = np.array([[0.20, 0.40], [0.60, np.nan]], dtype=np.float32)
        stats = calculate_index_statistics(arr)
        self.assertEqual(stats['valid_pixel_count'], 3)
        self.assertEqual(stats['total_pixel_count'], 4)
        self.assertAlmostEqual(stats['min_value'], 0.20, places=4)
        self.assertAlmostEqual(stats['max_value'], 0.60, places=4)
        self.assertAlmostEqual(stats['mean'], 0.40, places=4)
        self.assertAlmostEqual(stats['median'], 0.40, places=4)
        self.assertAlmostEqual(stats['std_dev'], 0.1633, places=3)

    def test_resampling_bilinear(self):
        # 2x2 upsampled to 4x4
        src_data = np.array([[10.0, 20.0], [30.0, 40.0]], dtype=np.float32)
        src_transform = Affine(20.0, 0.0, 0.0, 0.0, -20.0, 40.0)
        dst_transform = Affine(10.0, 0.0, 0.0, 0.0, -10.0, 40.0)
        dst_shape = (4, 4)

        resampled = resample_to_reference(
            source_data=src_data,
            source_transform=src_transform,
            source_crs="EPSG:32643",
            target_shape=dst_shape,
            target_transform=dst_transform,
            target_crs="EPSG:32643",
            resampling_method=Resampling.bilinear
        )
        self.assertEqual(resampled.shape, (4, 4))
        self.assertGreaterEqual(np.min(resampled), 9.0)
        self.assertLessEqual(np.max(resampled), 41.0)


class SpectralIndicesAPITests(APITestCase):
    def setUp(self):
        self.village = Village.objects.create(
            name="Piplantri Pilot",
            district="Rajsamand",
            state="Rajasthan",
            location=Point(73.8347, 25.0743, srid=4326),
            area_hectares=1050.0,
            population=5120
        )
        self.scene = SatelliteScene.objects.create(
            village=self.village,
            provider="AWS Earth Search (Element 84)",
            collection="sentinel-2-l2a",
            scene_id="S2B_43RCH_20240322_0_L2A",
            acquisition_date=timezone.now(),
            cloud_cover=0.0,
            processing_level="Level-2A",
            status="completed"
        )
        self.index_ndvi = SpectralIndex.objects.create(
            scene=self.scene,
            index_type="NDVI",
            file_path="satellite/indices/villages/1/S2B_43RCH_20240322_0_L2A/ndvi.tif",
            png_path="satellite/indices/villages/1/S2B_43RCH_20240322_0_L2A/ndvi.png",
            resolution=10.0,
            crs="EPSG:32643",
            min_value=-0.2419,
            max_value=0.8846,
            mean=0.2983,
            median=0.2369,
            std_dev=0.1709,
            valid_pixel_count=249984,
            total_pixel_count=250480,
            cloud_masked=True,
            cloud_pixel_count=496,
            status="completed"
        )

    def test_get_scene_indices_endpoint(self):
        url = reverse('scene-indices-list', kwargs={'pk': self.scene.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        data = response.data[0]
        self.assertEqual(data['index_type'], "NDVI")
        self.assertEqual(data['mean'], 0.2983)
        self.assertEqual(data['max_value'], 0.8846)
        self.assertIn("download_url", data)
        self.assertIn("png_url", data)

    def test_scene_detail_includes_indices(self):
        url = reverse('satellite-scene-detail', kwargs={'pk': self.scene.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['indices_count'], 1)
        self.assertEqual(response.data['indices'][0]['index_type'], "NDVI")
