from django.urls import reverse
from eudr_backend.models import EUDRSharedMapAccessCodeModel
from rest_framework.test import APIClient
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
import datetime
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token

from eudr_backend.models import (
    EUDRFarmModel,
    EUDRFarmBackupModel,
    EUDRCollectionSiteModel,
    EUDRUploadedFilesModel,
    EUDRSharedMapAccessCodeModel,
    WhispAPISetting
)


class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser', password='password123')
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        self.file = EUDRUploadedFilesModel.objects.create(
            file_name='test.csv', uploaded_by='testuser')
        self.farm = EUDRFarmModel.objects.create(
            remote_id="F123",
            farmer_name="Alice",
            farm_size=100.5,
            farm_village="Springfield",
            farm_district="District A",
            latitude=0.0,
            longitude=0.0,
            polygon={"type": "Polygon", "coordinates": [[[30.0645542, -1.965532], [
                30.064553, -1.9655323], [30.0645528, -1.9655322], [30.0645542, -1.965532]]]},
            accuracies=[],
            file_id=self.file.id
        )
        self.collection_site = EUDRCollectionSiteModel.objects.create(
            name='Test Site', device_id='12345')
        self.farm_backup = EUDRFarmBackupModel.objects.create(
            remote_id='1', site_id=self.collection_site)
        self.login_url = reverse("login")
        self.signup_url = reverse("signup")

    def test_get_request_returns_signup_template(self):
        """Test that a GET request renders the signup HTML template."""
        response = self.client.get(self.signup_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/signup.html")

    def test_post_request_valid_data_html(self):
        """Test that a POST request with valid data creates a user and redirects for HTML."""
        response = self.client.post(reverse("signup"), {
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe@gmail.com",
            "password1": "Ras34@@sd!cx",
            "password2": "Ras34@@sd!cx"
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/")
        self.assertTrue(User.objects.filter(
            username="johndoe@gmail.com").exists())

    def test_post_request_invalid_data_html(self):
        """Test that a POST request with invalid data re-renders the signup form for HTML."""
        response = self.client.post(reverse("signup"), data={
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe@gmail.com",
            "password1": "password123",
            "password2": "password456"
        }
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auth/signup.html")

    def test_post_request_valid_data_json(self):
        """Test that a POST request with valid data creates a user and returns a JSON response."""
        response = self.client.post(self.signup_url, {
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe@gmail.com",
            "password1": "Ras34@@sd!cx",
            "password2": "Ras34@@sd!cx"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json(), {
            "message": "Signup successful",
            "user": {"username": "johndoe@gmail.com"},
            "token": response.json()["token"]
        })
        self.assertTrue(User.objects.filter(
            username="johndoe@gmail.com").exists())

    def test_post_request_invalid_data_json(self):
        """Test that a POST request with invalid data returns an error in JSON."""
        response = self.client.post(self.signup_url, {
            "first_name": "John",
            "username": "johndoe@gmail.com",
            "password1": "password123",
            "password2": "password456"  # Passwords do not match
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.json())
        self.assertIn("password2", response.json()["errors"])

    def test_invalid_method(self):
        """Test that a method other than GET or POST returns a 405 Method Not Allowed."""
        response = self.client.put(
            self.signup_url, {}, format="json")
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_login_page(self):
        """
        Test GET request renders the login page.
        """
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/login.html')
        self.assertContains(response, '<form')

    def test_successful_login_html(self):
        """
        Test successful login with HTML form submission.
        """
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, 302)
        # Replace with your success page template
        self.assertRedirects(response, '/')

    def test_failed_login_html(self):
        """
        Test failed login with HTML form submission.
        """
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/login.html')

    def test_successful_login_json(self):
        """
        Test successful login with JSON request.
        """
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'password123'
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {
            "message": "Login successful",
            "user": {
                "username": "testuser"
            },
            "token": response.json()["token"]
        })

    def test_failed_login_json(self):
        """
        Test failed login with JSON request.
        """
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user(self):
        url = reverse('user_create')
        data = {'username': 'newuser', 'password': '12345'}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_users(self):
        # Create a superuser
        superuser = User.objects.create_superuser(
            username='superuser', password='superpassword')

        token = Token.objects.create(user=superuser)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        # Attempt to retrieve users
        url = reverse('user_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Log out superuser
        self.client.logout()

        # Log in as a regular user
        self.user = User.objects.create_user(
            username='testuser2', password='password123')
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        # Attempt to retrieve users
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
        # Ensure only superuser can delete a user
        superuser = User.objects.create_superuser(
            username='superuser', password='superpassword')
        token = Token.objects.create(user=superuser)
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + token.key)
        url = reverse('user_delete', args=[self.user.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_farm_data(self):
        url = reverse('create_farm_data')
        data = {"type": "FeatureCollection", "features": [{
            "type": "Feature",
            "properties": {
                "commodity": "COFFEE",
                "farmer_name": "sjee",
                "member_id": "",
                "collection_site": "fhfh",
                "agent_name": "fjf",
                "farm_village": "dhxfy",
                "farm_district": "fgud",
                "farm_size": 4.11,
                "latitude": 0,
                "longitude": 0
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[30.0645542, -1.965532], [30.064553, -1.9655323], [30.0645528, -1.9655322], [30.0645542, -1.965532]]]
            }
        }, {
            "type": "Feature",
            "properties": {
                "commodity": "COFFEE",
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
        }]}
        response = self.client.post(url, data, format='json')
        print("response code",response.status_code)
        print("response data",response.data)
        self.file.id = response.data['file_id']
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_sync_farm_data(self):
        url = reverse('sync_farm_data')
        data = [
            {
                "device_id": "b6cc4c5d-7e87-4edd-872a-3ffec8d92ed0",
                "collection_site": {
                    "local_cs_id": 4,
                    "name": "kitabi cs",
                            "agent_name": "jean bosco muhire",
                            "phone_number": "",
                            "email": "jbmuhire@gmail.com",
                            "village": "kitabi",
                            "district": "nyamagabe"
                },
                "farms": [
                    {
                        "remote_id": "0b2a5f2f-ada0-4163-840e-b2979659b85b",
                        "farmer_name": "shhb",
                        "member_id": "RW250",
                        "village": "kitabi",
                        "district": "nyamagabe",
                        "size": 1.5,
                        "latitude": -1.9310327,
                        "longitude": 30.138477,
                        "coordinates": [],
                        "accuracies": []
                    },
                ]
            }
        ]
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_restore_farm_data(self):
        url = reverse('restore_farm_data')
        data = {'device_id': '12345'}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_farm_data(self):
        url = reverse('update_farm_data', args=[self.farm.id])
        data = {
            'remote_id': 'F123',
            'farmer_name': 'Updated Farmer',
            'farm_size': 150.0,
            'farm_village': 'Updated Village',
            'farm_district': 'Updated District',
            'latitude': 36.0,
            'longitude': -81.0,
            'polygon': {"type": "Polygon", "coordinates": [
                [1, 2], [3, 4], [5, 6]]},
            'accuracies': [95, 90]
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

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

    def test_retrieve_file(self):
        url = reverse('retrieve_file', args=[self.file.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_download_template(self):
        url = reverse('download_template') + '?file_format=csv'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_generate_map_link(self):
        url = reverse('map_share')
        data = {'file-id': self.file.id}
        response = self.client.post(url, data, format="json")
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
        self.client = APIClient()
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

    @ patch('requests.get')
    def test_map_view_with_valid_access_code(self, mock_initialize_earth_engine):
        token = Token.objects.create(user=self.user)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

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

        token = Token.objects.create(user=self.user)

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        response = self.client.get(self.map_url, {
            'file-id': 'expired-file-id',
            'access-code': 'expired-code'
        })

        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(response.content, {
                             "message": "Access Code Expired", "status": 403})

    def test_map_view_with_invalid_access_code(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        response = self.client.get(self.map_url, {
            'file-id': 'invalid-file-id',
            'access-code': 'invalid-code'
        })

        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(response.content, {
                             "message": "Invalid file ID or access code.", "status": 403})
