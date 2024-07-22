from celery import shared_task
import requests
from .models import EUDRFarmModel


@shared_task
def update_farm_geoid():
    farms = EUDRFarmModel.objects.filter(geoid__isnull=True)
    for farm in farms:
        print(farm.polygon)
        payload = {
            "wkt": farm.polygon
        }
        response = requests.post(
            "https://api-ar.agstack.org/register-field-boundary", json=payload)
        if response.status_code == 200:
            data = response.json()
            farm.geoid = data.get("Geo Id")
            farm.save()
