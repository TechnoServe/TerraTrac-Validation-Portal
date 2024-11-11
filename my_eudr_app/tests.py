from django.test import TestCase
from eudr_backend.models import (
    EUDRUserModel,
    EUDRFarmModel,
    EUDRFarmBackupModel,
    EUDRCollectionSiteModel,
    EUDRUploadedFilesModel,
    EUDRSharedMapAccessCodeModel,
    WhispAPISetting
)
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError


class EUDRUserModelTest(TestCase):
    def setUp(self):
        self.user = EUDRUserModel.objects.create(
            first_name="John",
            last_name="Doe",
            username="john.doe@example.com",
            password="password123",
        )

    def test_user_model_str(self):
        """Test string representation of EUDRUserModel."""
        self.assertEqual(str(self.user), self.user.username)

    def test_invalid_user_type(self):
        """Test invalid user_type assignment."""
        invalid_user = EUDRUserModel(
            first_name="Jane",
            last_name="Smith",
            username="jane.smith@example.com",
            password="password123",
            user_type="INVALID_TYPE",  # Invalid choice
        )
        with self.assertRaises(ValidationError):
            invalid_user.full_clean()

    def test_user_model_unique_username(self):
        """Test unique constraint on username field."""
        EUDRUserModel.objects.create(
            first_name="Alice",
            last_name="Smith",
            username="alice.smith@example.com",
            password="password123",
        )

        with self.assertRaises(IntegrityError):
            EUDRUserModel.objects.create(
                first_name="Bob",
                last_name="Jones",
                username="alice.smith@example.com",  # Duplicate username
                password="password123",
            )


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
