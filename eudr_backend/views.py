import ast
import json
import httpx
from django.http import HttpResponse
from django.utils import timezone
import pandas as pd
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from asgiref.sync import async_to_sync, sync_to_async

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


# Define an async function
async def async_create_farm_data(data, serializer, file_id, format):
    errors = []
    created_data = []
    farm_data = data[0]["data"]["features"] if format == "json" else data[0]["data"]

    for item in farm_data:
        serializer = EUDRFarmModelSerializer(
            data=(
                {
                    "farmer_name": item["properties"]["farmer_name"],
                    "farm_size": item["properties"]["farm_size"],
                    "collection_site": item["properties"]["collection_site"],
                    "agent_name": item["properties"]["agent_name"],
                    "farm_village": item["properties"]["farm_village"],
                    "farm_district": item["properties"]["farm_district"],
                    "latitude": item["properties"]["latitude"],
                    "longitude": item["properties"]["longitude"],
                    "polygon": item["geometry"]["coordinates"][0],
                }
                if format == "json"
                else item
            )
        )
        # if farmer_name is empty, skip the record
        if not item["properties"]["farmer_name"]:
            continue

        # Check if a similar record already exists for each item
        if await EUDRFarmModel.objects.filter(
            farmer_name=item["properties"]["farmer_name"],
        ).aexists():
            errors.append(
                {
                    "error": "Duplicate entry. This combination already exists.",
                    "data": item,
                }
            )
        elif serializer.is_valid():
            # add the file_id to the serializer data
            serializer.validated_data["file_id"] = file_id
            coordinates = (
                item["geometry"]["coordinates"][0]
                if format == "json"
                else item["polygon"]
            )

            # do whisp analysis POST request
            url = "https://whisp-app-vdfqchwaca-uc.a.run.app/api/wkt"
            headers = {"Content-Type": "application/json"}
            body = {
                "wkt": "POLYGON(("
                + ",".join(f"{lon} {lat}" for lon, lat in coordinates)
                + "))",
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=body)
                response_data = response.json()

            item["analysis"] = response_data

            # add the analysis result to the serializer data
            serializer.validated_data["analysis"] = item["analysis"]

            # Save the serializer data with the external analysis result
            await sync_to_async(serializer.save)()
            created_data.append(serializer.data)
        else:
            # delete the file if the serializer is not valid
            EUDRUploadedFilesModel.objects.get(id=file_id).delete()
            errors.append({"error": serializer.errors, "data": item})

    return errors, created_data


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
    # Call the async function from sync context
    errors, created_data = async_to_sync(async_create_farm_data)(
        data, serializer, file_id, request.data.get("format")
    )

    if errors:
        # delete the file if there are errors
        EUDRUploadedFilesModel.objects.get(id=file_id).delete()
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    return Response(created_data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def retrieve_farm_data(request):
    data = EUDRFarmModel.objects.all().order_by("-updated_at")

    serializer = EUDRFarmModelSerializer(data, many=True)

    return Response(serializer.data)


@api_view(["GET"])
def retrieve_farm_detail(request, pk):
    data = EUDRFarmModel.objects.get(id=pk)
    serializer = EUDRFarmModelSerializer(data, many=False)
    return Response(serializer.data)


@api_view(["GET"])
def retrieve_farm_data_from_file_id(request, pk):
    data = EUDRFarmModel.objects.filter(file_id=pk)
    serializer = EUDRFarmModelSerializer(data, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def retrieve_files(request):
    data = EUDRUploadedFilesModel.objects.all().order_by("-updated_at")
    serializer = EUDRUploadedFilesModelSerializer(data, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def download_template(request):
    format_val = request.GET.urlencode().split("%3D")[1]
    format = format_val.split("=")[0]

    # Create a sample template dataframe
    data = {
        "farmer_name": "John Doe",
        "farm_size": 4,
        "collection_site": "Site A",
        "farm_village": "Village A",
        "farm_district": "District A",
        "latitude": "-1.62883139933721",
        "longitude": "29.9898212498949",
        "polygon": "[[41.8781, 87.6298], [41.8781, 87.6299]]",
    }

    df = pd.DataFrame([data])

    timestamp_str = timezone.now().strftime("%Y-%m-%d-%H-%M-%S")

    if format == "csv":
        response = HttpResponse(content_type="text/csv")
        filename = f"eudr-upload-template-{timestamp_str}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        df.to_csv(response, index=True)
    elif format == "json":
        response = HttpResponse(content_type="application/json")
        filename = f"eudr-upload-template-{timestamp_str}.json"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        # GeoJSON format will depend on your specific data structure
        # This is just an example
        geojson_data = {"type": "FeatureCollection", "features": []}
        response.write(json.dumps(geojson_data))
    else:
        return Response({"error": "Invalid format"}, status=status.HTTP_400_BAD_REQUEST)

    return response
