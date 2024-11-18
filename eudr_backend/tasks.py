import requests
from shapely import Polygon

from eudr_backend import settings
from .models import EUDRFarmModel, EUDRUploadedFilesModel
from background_task import background
from shapely import wkt

AG_BASE_URL = "https://api-ar.agstack.org"


def get_access_token():
    login_url = f'{AG_BASE_URL}/login'
    payload = {
        "email": settings.AGSTACK_EMAIL,
        "password": settings.AGSTACK_PASSWORD
    }
    response = requests.post(login_url, json=payload)
    response.raise_for_status()  # Raise an error for bad responses
    data = response.json()
    return data['access_token']


@background(schedule=60)  # Schedule task to run every 5 minutes
def update_geoid(user_id):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    # Get all file IDs corresponding to the user
    user_files = EUDRUploadedFilesModel.objects.filter(uploaded_by=user_id)
    file_ids = user_files.values_list('id', flat=True)

    # Filter farms based on these file IDs and geoid being null
    farms = EUDRFarmModel.objects.filter(
        geoid__isnull=True, file_id__in=file_ids)
    for farm in farms:
        # check if polygon has only one ring
        if len(farm.polygon) != 1:
            continue

        reversed_coords = [[(lat, lon) for lat, lon in ring]
                           for ring in farm.polygon]

# Create a Shapely Polygon
        polygon = Polygon(reversed_coords[0])

        # Convert to WKT format
        wkt_format = wkt.dumps(polygon)

        response = requests.post(
            f'{AG_BASE_URL}/register-field-boundary',
            json={"wkt": wkt_format},
            headers=headers
        )
        data = response.json()
        if response.status_code == 200:
            farm.geoid = data.get("Geo Id")
            farm.save()
        else:
            farm.geoid = data.get("matched geo ids")[0]
            farm.save()
