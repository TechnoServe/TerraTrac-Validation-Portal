import json
import os
from django.http import HttpResponse
from django.utils import timezone
from dotenv import load_dotenv
import pandas as pd
import requests
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from eudr_backend.models import EUDRFarmModel
from .serializers import EUDRFarmModelSerializer


@api_view(["POST"])
def create_farm_data(request):
    serializer = EUDRFarmModelSerializer(data=request.data)

    data = request.data

    if not isinstance(data, list):
        data = [data]

    errors = []
    created_data = []

    for item in data:
        serializer = EUDRFarmModelSerializer(data=item)

        # Check if a similar record already exists for each item
        if EUDRFarmModel.objects.filter(
            farmer_name=item.get("farmer_name"),
            plantation_name=item.get("plantation_name"),
            plantation_code=item.get("plantation_code"),
        ).exists():
            errors.append(
                {
                    "error": "Duplicate entry. This combination already exists.",
                    "data": item,
                }
            )
        elif serializer.is_valid():
            serializer.save()
            created_data.append(serializer.data)
        else:
            errors.append({"error": serializer.errors, "data": item})

    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    return Response(created_data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def retrieve_farm_data(request):
    data = EUDRFarmModel.objects.all()
    serializer = EUDRFarmModelSerializer(data, many=True)
    return Response(serializer.data)


@api_view(["POST"])
def get_radd_data(request):
    # token = get_auth_token()
    # if not token:
    #     return Response({"error": "Failed to get auth token"}, status=500)

    # api_key_response = get_api_key(token)
    # if not api_key_response or "api_key" not in api_key_response:
    #     return Response({"error": "Failed to get API key"}, status=500)

    load_dotenv()

    api_key = os.getenv("API_KEY")

    url = f"{os.getenv('API_BASE_URL')}/dataset/wur_radd_alerts/latest/query"
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    response = requests.post(url, headers=headers, json=request.data)

    if response.status_code == 200:
        return Response(response.json())
    else:
        return Response(response.json(), status=response.status_code)


@api_view(["GET"])
def download_template(request):
    format_val = request.GET.urlencode().split("%3D")[1]
    format = format_val.split("=")[0]

    # Create a sample template dataframe
    data = {
        "farmer_name": ["John Doe", "Jane Smith"],
        "farm_size": [10.5, 8.2],
        "collection_site": ["Site A", "Site B"],
        "farm_village": ["Village A", "Village B"],
        "farm_district": ["District A", "District B"],
        "farm_coordinates": ['["40.7128", "74.0060"]', '["41.8781", "87.6298"]'],
        "farm_polygon_coordinates": [
            '[["40.7128", "74.0060"], ["40.7128", "74.0061"]]',
            '[["41.8781", "87.6298"], ["41.8781", "87.6299"]]',
        ],
        "plantation_name": ["Plantation 1", "Plantation 2"],
        "plantation_code": ["P001", "P002"],
        "is_validated": [True, False],
        "validated_at": ["2024-04-15T12:00:00Z", None],
    }

    df = pd.DataFrame(data)

    timestamp_str = timezone.now().strftime("%Y-%m-%d-%H-%M-%S")

    if format == "csv":
        response = HttpResponse(content_type="text/csv")
        filename = f"eudr-upload-template-{timestamp_str}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        df.to_csv(response, index=False)
    elif format == "excel":
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filename = f"eudr-upload-template-{timestamp_str}.xlsx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        df.to_excel(response, index=False)
    elif format == "geojson":
        response = HttpResponse(content_type="application/json")
        filename = f"eudr-upload-template-{timestamp_str}.geojson"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        # GeoJSON format will depend on your specific data structure
        # This is just an example
        geojson_data = {"type": "FeatureCollection", "features": []}
        response.write(json.dumps(geojson_data))
    else:
        return Response({"error": "Invalid format"}, status=status.HTTP_400_BAD_REQUEST)

    return response
