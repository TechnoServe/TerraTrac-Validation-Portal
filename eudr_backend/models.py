from my_eudr_app import models


class EUDRFarmModel(models.models.Model):
    farmer_name = models.models.CharField(max_length=255)
    farm_size = models.models.FloatField()
    collection_site = models.models.CharField(max_length=255)
    farm_village = models.models.CharField(max_length=255)
    farm_coordinates = models.models.JSONField()
    farm_polygon_coordinates = models.models.JSONField()
    plantation_name = models.models.CharField(max_length=255)
    plantation_code = models.models.CharField(max_length=255)
    is_validated = models.models.BooleanField()
    is_eudr_compliant = models.models.BooleanField(default=False)
    validated_at = models.models.DateTimeField(null=True, blank=True)
    created_at = models.models.DateTimeField(auto_now_add=True)
    updated_at = models.models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.farmer_name
