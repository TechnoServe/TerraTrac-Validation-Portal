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

from eudr_backend.models import EUDRFarmModel, EUDRUploadedFilesModel, EUDRUserModel
from .serializers import (
    EUDRFarmModelSerializer,
    EUDRUploadedFilesModelSerializer,
    EUDRUserModelSerializer,
)


@api_view(["POST"])
def create_user(request):
    serializer = EUDRUserModelSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def retrieve_users(request):
    data = EUDRUserModel.objects.all()
    serializer = EUDRUserModelSerializer(data, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def retrieve_user(request, pk):
    user = EUDRUserModel.objects.get(id=pk)
    serializer = EUDRUserModelSerializer(user, many=False)
    return Response(serializer.data)


@api_view(["PUT"])
def update_user(request, pk):
    user = EUDRUserModel.objects.get(id=pk)
    serializer = EUDRUserModelSerializer(instance=user, data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
def delete_user(request, pk):
    user = EUDRUserModel.objects.get(id=pk)
    user.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
def create_farm_data(request):
    serializer = EUDRFarmModelSerializer(data=request.data)

    # combine file_name and format to save in the database with dummy uploaded_by. then retrieve the file_id
    file_data = {
        "file_name": f"{request.data.get('file_name')}.{request.data.get('format')}",
        "uploaded_by": "admin",
    }
    file_serializer = EUDRUploadedFilesModelSerializer(data=file_data)

    if file_serializer.is_valid():
        file_serializer.save()
        file_id = file_serializer.data.get("id")
    else:
        return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = request.data

    if not isinstance(data, list):
        data = [data]

    errors = []
    created_data = []

    farm_data = data[0]["data"]

    for item in farm_data:
        serializer = EUDRFarmModelSerializer(data=item)

        # if farmer_name is empty, skip the record
        if not item.get("farmer_name"):
            continue

        # Check if a similar record already exists for each item
        if EUDRFarmModel.objects.filter(
            farmer_name=item.get("farmer_name"),
        ).exists():
            # send new API request to validate the data from get-radd-data endpoint
            # data = {
            #     "geometry": {
            #         "coordinates": [[item.get("farm_polygon_coordinates")]],
            #         "type": "Polygon",
            #     },
            #     "sql": "SELECT longitude, latitude, wur_radd_alerts__date, wur_radd_alerts__confidence FROM results",
            # }

            # # do post request on api/get-radd-data/ endpoint
            # url = "http://127.0.0.1:8000/api/get-radd-data/"

            # # Sending the POST request
            # response = requests.post(url, json=json.dumps(data))

            # print(response)

            errors.append(
                {
                    "error": "Duplicate entry. This combination already exists.",
                    "data": item,
                }
            )
        elif serializer.is_valid():
            # add the file_id to the serializer data
            serializer.validated_data["file_id"] = file_id

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


@api_view(["GET"])
def retrieve_files(request):
    data = EUDRUploadedFilesModel.objects.all()
    serializer = EUDRUploadedFilesModelSerializer(data, many=True)
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
        "farmer_name": "Mama Magufuli",
        "farm_size": 8.2,
        "collection_site": "Site A",
        "farm_village": "Village A",
        "farm_district": "District A",
        "latitude": "-1.62883139933721",
        "longitude": "29.9898212498949",
        "polygon": (
            '[("41.8781", "87.6298"), ("41.8781", "87.6299")]'
            if format == "csv"
            else [[41.8781, 87.6298], [41.8781, 87.6299]]
        ),
        "created_at": "2021-09-01T00:00:00Z",
        "updated_at": "2021-09-01T00:00:00Z",
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
