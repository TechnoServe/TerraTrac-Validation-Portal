import requests
from shapely import Polygon

from eudr_backend import settings
from .models import EUDRFarmModel
from background_task import background
from shapely import wkt


def get_access_token():
    login_url = "https://api-ar.agstack.org/login"
    payload = {
        "email": settings.AGSTACK_EMAIL,
        "password": settings.AGSTACK_PASSWORD
    }
    response = requests.post(login_url, json=payload)
    response.raise_for_status()  # Raise an error for bad responses
    data = response.json()
    return data['access_token']


@background(schedule=300)  # Schedule task to run every 5 minutes
def update_geoid():
    print("The update_geoid task is running.")
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    farms = EUDRFarmModel.objects.filter(geoid__isnull=True)
    for farm in farms:
        # check if polygon has only one ring
        if len(farm.polygon) != 1:
            continue

        reversed_coords = [[(lon, lat) for lat, lon in ring]
                           for ring in farm.polygon]

# Create a Shapely Polygon
        polygon = Polygon(reversed_coords[0])

        # Convert to WKT format
        wkt_format = wkt.dumps(polygon)

        response = requests.post(
            "https://api-ar.agstack.org/register-field-boundary",
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
            print(f"""Failed to fetch geoid for farm {
                farm.id}: {response.status_code}""")
