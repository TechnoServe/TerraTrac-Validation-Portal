from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


class IntegrationTests(TestCase):
    # User and Authentication Tests
    def test_user_signup_and_login_flow(self):
        # Signup
        signup_response = self.client.post(reverse('signup'), {
            'username': 'testuser',
            'password1': 'testpassword',
            'password2': 'testpassword',
        })
        self.assertEqual(signup_response.status_code, 302)
        self.assertTrue(User.objects.filter(username='testuser').exists())

        # Login
        login_response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpassword',
        })
        self.assertEqual(login_response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)

        # Logout
        token = Token.objects.get(user__username='testuser')
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        logout_response = self.client.post(reverse('logout'))
        self.assertEqual(logout_response.status_code, 302)
        self.assertFalse('_auth_user_id' in self.client.session)

        # Cleanup
        User.objects.filter(username='testuser').delete()

    # Template Rendering Tests
    def test_signup_template_renders_correctly(self):
        response = self.client.get(reverse('signup'))
        self.assertTemplateUsed(response, 'auth/signup.html')

    def test_login_template_renders_correctly(self):
        response = self.client.get(reverse('login'))
        self.assertTemplateUsed(response, 'auth/login.html')

    # Full Flow Tests
    def test_full_farm_data_flow(self):
        # Signup
        signup_response = self.client.post(reverse('signup'), {
            'username': 'testuser',
            'password1': 'testpassword',
            'password2': 'testpassword',
        })
        self.assertEqual(signup_response.status_code, 302)
        self.assertTrue(User.objects.filter(username='testuser').exists())

        # Login
        login_response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpassword',
        })
        self.assertEqual(login_response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)

        user = User.objects.get(username='testuser')

        # Generate token for the user
        token, created = Token.objects.get_or_create(user=user)
        self.assertIsNotNone(token.key)
        self.client = APIClient()

        # Use the token in subsequent requests
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        # Sync Farm Data
        data = {"type": "FeatureCollection", "features": [{
            "type": "Feature",
            "properties": {
                "remote_id": "1b8313c1-c584-4e6b-8a1c-3e9fd962798b",
                "commodity": "COFFEE",
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
        create_response = self.client.post(
            reverse('create_farm_data'), data, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        # Retrieve Farm Data
        retrieve_response = self.client.get(reverse('retrieve_farm_data'))
        self.assertEqual(retrieve_response.status_code, 200)
        self.assertIsInstance(retrieve_response.json(), list)
        self.assertGreater(len(retrieve_response.json()), 0)

        # Cleanup
        User.objects.filter(username='testuser').delete()
