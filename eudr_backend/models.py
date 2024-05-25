from my_eudr_app import models


# create enum for user type
class UserType(models.models.enums.Choices):
    AGENT = "AGENT"
    ADMIN = "ADMIN"


class EUDRUserModel(models.models.Model):
    first_name = models.models.CharField(max_length=255)
    last_name = models.models.CharField(max_length=255)
    email = models.models.EmailField(max_length=255, unique=True)
    phone_number = models.models.CharField(max_length=255)
    password = models.models.CharField(max_length=255)
    is_active = models.models.BooleanField(default=True)
    user_type = models.models.CharField(
        max_length=255, choices=UserType.choices, default=UserType.ADMIN
    )
    created_at = models.models.DateTimeField(auto_now_add=True)
    updated_at = models.models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email


class EUDRFarmModel(models.models.Model):
    farmer_name = models.models.CharField(max_length=255)
    farm_size = models.models.FloatField()
    collection_site = models.models.CharField(max_length=255)
    agent_name = models.models.CharField(max_length=255, null=True, blank=True)
    farm_village = models.models.CharField(max_length=255)
    farm_district = models.models.CharField(max_length=255)
    latitude = models.models.FloatField(default=0.0)
    longitude = models.models.FloatField(default=0.0)
    polygon = models.models.JSONField()
    is_validated = models.models.BooleanField(default=False)
    is_eudr_compliant = models.models.BooleanField(default=False)
    analysis = models.models.JSONField(null=True, blank=True)
    validated_at = models.models.DateTimeField(null=True, blank=True)
    file_id = models.models.CharField(max_length=255, null=True, blank=True)
    created_at = models.models.DateTimeField(auto_now_add=True)
    updated_at = models.models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.farmer_name


class EUDRUploadedFilesModel(models.models.Model):
    file_name = models.models.CharField(max_length=255)
    uploaded_by = models.models.CharField(max_length=255)
    created_at = models.models.DateTimeField(auto_now_add=True)
    updated_at = models.models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.file_name