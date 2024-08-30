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
    remote_id = models.models.CharField(max_length=255, null=True, blank=True)
    farmer_name = models.models.CharField(max_length=255)
    member_id = models.models.CharField(max_length=255, null=True, blank=True)
    farm_size = models.models.FloatField()
    collection_site = models.models.CharField(max_length=255, blank=True)
    site_id = models.models.ForeignKey(
        "EUDRCollectionSiteModel", on_delete=models.models.CASCADE, null=True, blank=True)
    agent_name = models.models.CharField(max_length=255, null=True, blank=True)
    farm_village = models.models.CharField(max_length=255)
    farm_district = models.models.CharField(max_length=255)
    latitude = models.models.FloatField(default=0.0)
    longitude = models.models.FloatField(default=0.0)
    polygon = models.models.JSONField()
    geoid = models.models.CharField(max_length=255, null=True, blank=True)
    is_validated = models.models.BooleanField(default=False)
    analysis = models.models.JSONField(null=True, blank=True)
    validated_at = models.models.DateTimeField(null=True, blank=True)
    file_id = models.models.CharField(max_length=255, null=True, blank=True)
    created_at = models.models.DateTimeField(auto_now_add=True)
    updated_at = models.models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.farmer_name


class EUDRCollectionSiteModel(models.models.Model):
    site_name = models.models.CharField(max_length=255)
    site_district = models.models.CharField(max_length=255)
    site_manager = models.models.CharField(max_length=255, null=True)
    site_village = models.models.CharField(max_length=255)
    site_email = models.models.EmailField(
        max_length=255, null=True, blank=True)
    site_phone_number = models.models.CharField(
        max_length=255, null=True, blank=True)
    created_at = models.models.DateTimeField(auto_now_add=True)
    updated_at = models.models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.site_name


class EUDRUploadedFilesModel(models.models.Model):
    file_name = models.models.CharField(max_length=255)
    device_id = models.models.CharField(max_length=255, null=True, blank=True)
    uploaded_by = models.models.CharField(max_length=255)
    created_at = models.models.DateTimeField(auto_now_add=True)
    updated_at = models.models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.file_name


class WhispAPISetting(models.models.Model):
    chunk_size = models.models.PositiveIntegerField(
        default=500, help_text="Size of WHISP API data chunks to fetch.")

    def __str__(self):
        return f"Whisp API Settings (Chunk Size: {self.chunk_size})"
