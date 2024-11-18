from django.urls import reverse
from eudr_backend.models import EUDRSharedMapAccessCodeModel
from django.test import Client
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
import datetime
from django.contrib.auth.models import User
from rest_framework import status

from eudr_backend.models import (
    EUDRUserModel,
    EUDRFarmModel,
    EUDRFarmBackupModel,
    EUDRCollectionSiteModel,
    EUDRUploadedFilesModel,
    EUDRSharedMapAccessCodeModel,
    WhispAPISetting
)


class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='johndoe', password='12345')
        self.client.login(username='testuser', password='12345')
        self.eudr_user = EUDRUserModel.objects.create(
            first_name="John",
            last_name="Doe",
            username=self.user.username,
            password=self.user.password,
        )
        self.farm = EUDRFarmModel.objects.create(
            remote_id="F123",
            farmer_name="Alice",
            farm_size=100.5,
            farm_village="Springfield",
            farm_district="District A",
            latitude=35.0,
            longitude=-80.0,
            polygon={"type": "Polygon", "coordinates": [
                [1, 2], [3, 4], [5, 6]]},
            accuracies=[95, 90])
        self.file = EUDRUploadedFilesModel.objects.create(
            file_name='test.csv', uploaded_by='testuser')
        self.collection_site = EUDRCollectionSiteModel.objects.create(
            name='Test Site', device_id='12345')
        self.farm_backup = EUDRFarmBackupModel.objects.create(
            remote_id='1', site_id=self.collection_site)

    def test_create_user(self):
        url = reverse('create_user')
        data = {'username': 'newuser', 'password': '12345'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_users(self):
        url = reverse('retrieve_users')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_user(self):
        url = reverse('user_detail', args=[self.user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_user(self):
        url = reverse('user_update', args=[self.user.id])
        data = {'username': 'updateduser'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_user(self):
        url = reverse('user_delete', args=[self.user.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_farm_data(self):
        url = reverse('create_farm_data')
        data = {'format': 'geojson', 'data': {"type": "FeatureCollection", "features": [{
            "type": "Feature",
            "properties": {
                "remote_id": "1b8313c1-c584-4e6b-8a1c-3e9fd962798b",
                "farmer_name": "sjee",
                "member_id": "",
                "collection_site": "fhfh",
                "agent_name": "fjf",
                "farm_village": "dhxfy",
                "farm_district": "fgud",
                "farm_size": 1.11,
                "latitude": -1.965532,
                "longitude": 30.064553,
                "created_at": "Mon Sep 30 12:52:09 GMT+02:00 2024",
                "updated_at": "Mon Sep 30 12:52:09 GMT+02:00 2024"

            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[30.0645542, -1.965532], [30.064553, -1.9655323], [30.0645528, -1.9655322], [30.0645542, -1.965532]]]
            }
        }, {
            "type": "Feature",
            "properties": {
                "remote_id": "8317a3ca-c1c2-4990-98e4-055fbd8e4e19",
                "farmer_name": "shdh",
                "member_id": "",
                "collection_site": "fhfh",
                "agent_name": "fjf",
                "farm_village": "dhdh",
                "farm_district": "chxf",
                "farm_size": 1.0,
                "latitude": -1.965526,
                "longitude": 30.064561,
                "created_at": "Mon Sep 30 12:51:19 GMT+02:00 2024",
                "updated_at": "Mon Sep 30 12:51:19 GMT+02:00 2024"

            },
            "geometry": {
                "type": "Point",
                "coordinates": [-1.965526, 30.064561]
            }
        }]}}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sync_farm_data(self):
        url = reverse('sync_farm_data')
        data = [{'device_id': "b6cc4c5d-7e87-4edd-872a-3ffec8d92ed0", 'collection_site': {'name': 'Test Site'},
                 'farms': [{'remote_id': '0b2a5f2f-ada0-4163-840e-b2979659b85b'}]}]
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_restore_farm_data(self):
        url = reverse('restore_farm_data')
        data = {'device_id': '12345'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_farm_data(self):
        url = reverse('update_farm_data', args=[self.farm.id])
        data = {'name': 'Updated Farm'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_revalidate_farm_data(self):
        url = reverse('revalidate_farm_data', args=[self.file.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_farm_data(self):
        url = reverse('retrieve_farm_data')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_overlapping_farm_data(self):
        url = reverse('retrieve_overlapping_farm_data', args=[self.file.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_user_farm_data(self):
        url = reverse('retrieve_user_farm_data', args=[self.user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_all_synced_farm_data(self):
        url = reverse('retrieve_all_synced_farm_data')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_all_synced_farm_data_by_cs(self):
        url = reverse('retrieve_all_synced_farm_data_by_cs',
                      args=[self.collection_site.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_collection_sites(self):
        url = reverse('retrieve_collection_sites')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_map_data(self):
        url = reverse('retrieve_map_data')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_farm_detail(self):
        url = reverse('retrieve_farm_detail', args=[self.farm.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_farm_data_from_file_id(self):
        url = reverse('retrieve_farm_data_from_file_id', args=[self.file.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_files(self):
        url = reverse('retrieve_files')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_s3_files(self):
        url = reverse('retrieve_s3_files')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_file(self):
        url = reverse('retrieve_file', args=[self.file.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_download_template(self):
        url = reverse('download_template') + '?format=csv'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_map_link(self):
        url = reverse('generate_map_link')
        data = {'file-id': self.file.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class EUDRFarmModelTest(TestCase):
    def setUp(self):
        self.farm = EUDRFarmModel.objects.create(
            remote_id="F123",
            farmer_name="Alice",
            farm_size=100.5,
            farm_village="Springfield",
            farm_district="District A",
            latitude=35.0,
            longitude=-80.0,
            polygon={"type": "Polygon", "coordinates": [
                [1, 2], [3, 4], [5, 6]]},
            accuracies=[95, 90],
        )

    def test_farm_model_str(self):
        """Test string representation of EUDRFarmModel."""
        self.assertEqual(str(self.farm), self.farm.farmer_name)

    def test_farm_model_validation(self):
        """Test EUDRFarmModel field validations."""
        # Test required fields
        self.assertEqual(self.farm.farmer_name, "Alice")
        self.assertEqual(self.farm.farm_size, 100.5)

        # Check the polygon JSON field
        self.assertEqual(self.farm.polygon["type"], "Polygon")
        self.assertEqual(self.farm.accuracies, [95, 90])

    def test_farm_model_has_id_field(self):
        """Test that EUDRFarmModel has a valid ID field."""
        self.assertIsNotNone(self.farm.id)

    def test_farm_model_has_remote_id(self):
        """Test that EUDRFarmModel has a valid remote_id."""
        self.assertEqual(self.farm.remote_id, "F123")


class EUDRFarmBackupModelTest(TestCase):
    def setUp(self):
        self.collection_site = EUDRCollectionSiteModel.objects.create(
            name="Site A",
            local_cs_id="CS123",
            device_id="D123",
            village="Village A",
            district="District A",
        )
        self.farm_backup = EUDRFarmBackupModel.objects.create(
            remote_id="F123",
            farmer_name="Jane",
            size=50.0,
            site_id=self.collection_site,  # Use ID here
            village="Village B",
            district="District B",
        )

    def test_farm_backup_str(self):
        """Test string representation of EUDRFarmBackupModel."""
        self.assertEqual(str(self.farm_backup), self.farm_backup.remote_id)

    def test_farm_backup_collection_site_id(self):
        """Test that the collection site ID is correctly saved and used."""
        self.assertEqual(self.farm_backup.site_id,
                         self.collection_site)

    def test_farm_backup_has_id_field(self):
        """Test that EUDRFarmBackupModel has a valid ID field."""
        self.assertIsNotNone(self.farm_backup.id)


class EUDRCollectionSiteModelTest(TestCase):
    def setUp(self):
        self.site = EUDRCollectionSiteModel.objects.create(
            name="Site A",
            local_cs_id="CS123",
            device_id="D123",
            village="Village A",
            district="District A",
        )

    def test_collection_site_str(self):
        """Test string representation of EUDRCollectionSiteModel."""
        self.assertEqual(str(self.site), self.site.name)

    def test_collection_site_has_id_field(self):
        """Test that EUDRCollectionSiteModel has a valid ID field."""
        self.assertIsNotNone(self.site.id)


class EUDRUploadedFilesModelTest(TestCase):
    def setUp(self):
        self.uploaded_file = EUDRUploadedFilesModel.objects.create(
            file_name="farm_data.csv",
            uploaded_by="admin",
        )

    def test_uploaded_file_str(self):
        """Test string representation of EUDRUploadedFilesModel."""
        self.assertEqual(str(self.uploaded_file), self.uploaded_file.file_name)

    def test_uploaded_file_has_id_field(self):
        """Test that EUDRUploadedFilesModel has a valid ID field."""
        self.assertIsNotNone(self.uploaded_file.id)


class EUDRSharedMapAccessCodeModelTest(TestCase):
    def setUp(self):
        self.access_code = EUDRSharedMapAccessCodeModel.objects.create(
            file_id="F123",
            access_code="XYZ123",
            valid_until="2024-12-31T23:59:59Z",
        )

    def test_access_code_str(self):
        """Test string representation of EUDRSharedMapAccessCodeModel."""
        self.assertEqual(str(self.access_code), self.access_code.file_id)

    def test_access_code_has_id_field(self):
        """Test that EUDRSharedMapAccessCodeModel has a valid ID field."""
        self.assertIsNotNone(self.access_code.id)


class WhispAPISettingTest(TestCase):
    def setUp(self):
        self.whisp_setting = WhispAPISetting.objects.create(
            chunk_size=1000
        )

    def test_whisp_api_setting_str(self):
        """Test string representation of WhispAPISetting."""
        self.assertEqual(str(self.whisp_setting),
                         "Whisp API Settings (Chunk Size: 1000)")


class PerformanceTests(TestCase):
    def test_large_jsonfield(self):
        """Test performance with large JSONField."""
        farm = EUDRFarmModel.objects.create(
            farmer_name="Big Farm",
            farm_size=1000.0,
            polygon={"type": "Polygon", "coordinates": [
                [i, i+1] for i in range(1000)]},
        )
        self.assertEqual(farm.polygon["type"], "Polygon")


class MapViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Adjust this based on your URL configuration
        self.map_url = reverse('map_view')

        # Create and log in a test user
        self.user = User.objects.create_user(
            username='testuser', password='testpassword')
        self.client.force_login(self.user)

        # Create a valid access code record
        self.access_code_record = EUDRSharedMapAccessCodeModel.objects.create(
            file_id='1',
            access_code='23c4b3d4-4b3d-4b3d-4b3d-4b3d4b3d4b3d',
            valid_until=timezone.now() + datetime.timedelta(days=90)
        )

    @patch('requests.get')
    def test_map_view_with_valid_access_code(self, mock_initialize_earth_engine):
        response = self.client.get(
            self.map_url + '?file-id=1&access-code=23c4b3d4-4b3d-4b3d-4b3d-4b3d4b3d4b3d')

        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response['Content-Type'])

    def test_map_view_with_expired_access_code(self):
        expired_access_code = EUDRSharedMapAccessCodeModel.objects.create(
            file_id='expired-file-id',
            access_code='expired-code',
            valid_until=timezone.now() - datetime.timedelta(days=1)
        )

        response = self.client.get(self.map_url, {
            'file-id': 'expired-file-id',
            'access-code': 'expired-code'
        })

        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(response.content, {
                             "message": "Access Code Expired", "status": 403})

    def test_map_view_with_invalid_access_code(self):
        response = self.client.get(self.map_url, {
            'file-id': 'invalid-file-id',
            'access-code': 'invalid-code'
        })

        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(response.content, {
                             "message": "Invalid file ID or access code.", "status": 403})

    @patch('requests.get')
    def test_map_view_without_access_code(self, mock_initialize_earth_engine):
        response = self.client.get(self.map_url, {
            'lat': '10.0',
            'lon': '20.0'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response['Content-Type'])
