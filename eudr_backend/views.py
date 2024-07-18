import ast
import csv
import io
import json
import ee
from django.http import HttpResponse
from django.utils import timezone
import httpx
import pandas as pd
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from shapely.geometry import Polygon, Point
from asgiref.sync import async_to_sync, sync_to_async

from eudr_backend.models import EUDRFarmModel, EUDRUploadedFilesModel, EUDRUserModel
from eudr_backend.settings import initialize_earth_engine
from .serializers import (
    EUDRFarmModelSerializer,
    EUDRUploadedFilesModelSerializer,
    EUDRUserModelSerializer,
)

REQUIRED_FIELDS = [
    'collection_site',
    'farm_size',
    'farm_district',
    'farm_village',
    'latitude',
    'longitude'
]

GEOJSON_REQUIRED_FIELDS = REQUIRED_FIELDS + ['geometry']


def validate_geojson(data):
    errors = []
    if 'features' not in data or not isinstance(data['features'], list):
        return ['Invalid data format: "features" must be a list']

    for i, feature in enumerate(data['features']):
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})

        for field in GEOJSON_REQUIRED_FIELDS:
            if field == 'geometry':
                if 'coordinates' not in geometry:
                    errors.append(
                        f'Feature {i}: "geometry.coordinates" is required.')
            # elif properties.get(field) in [None, '']:
            #     errors.append(f"""Feature {i}: "{
            #                   field}" is required and cannot be empty.""")

    return errors


def validate_csv(data):
    errors = []

    # Check if data is a list of dictionaries
    if isinstance(data, list):
        # Remove last row if it's empty or contains specific values
        if data and (not data[-1] or data[-1].get('farmer_name') == '' or data[-1] == {"": ""}):
            data.pop()

        for i, row in enumerate(data):
            for field in REQUIRED_FIELDS:
                if field not in row or row[field] in [None, '', '0']:
                    errors.append(
                        f'Row {i}: "{field}" is required and cannot be empty or zero.')
    else:
        reader = csv.DictReader(io.StringIO(data))
        rows = list(reader)

        # Remove last row if it's empty or contains specific values
        if rows and (not rows[-1] or rows[-1].get('farmer_name') == '' or rows[-1] == {"": ""}):
            rows.pop()

        for i, row in enumerate(rows):
            for field in REQUIRED_FIELDS:
                if field not in row or row[field] in [None, '', '0']:
                    errors.append(
                        f'Row {i}: "{field}" is required and cannot be empty or zero.')

    return errors


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
async def async_create_farm_data(data, serializer, file_id, isSyncing=False):
    errors = []
    created_data = []

    if isSyncing:
        serializer = EUDRFarmModelSerializer(data=data)

        # if remote_id is already in the database, update the record, otherwise create a new record
        exists = await sync_to_async(EUDRFarmModel.objects.filter(remote_id=data["remote_id"]).exists)()
        if exists:
            # update the record
            farm_data = await sync_to_async(EUDRFarmModel.objects.get)(remote_id=data["remote_id"])
            serializer = EUDRFarmModelSerializer(farm_data, data=data)
            if serializer.is_valid():
                # perform the update immediately on remote_id
                await sync_to_async(serializer.save)()
                created_data.append(serializer.data)
        else:
            if serializer.is_valid():
                # add the file_id to the serializer data
                serializer.validated_data["file_id"] = file_id
                if (
                    len(data["polygon"])
                    <= 1
                ):
                    data["analysis"] = None
                else:
                    # do general analysis POST request
                    response_data = None
                    url = "https://whisp.openforis.org/api/geojson"
                    headers = {"Content-Type": "application/json"}
                    body = data
                    async with httpx.AsyncClient(timeout=600.0) as client:
                        response = await client.post(url, headers=headers, json=body)
                        response_data = response.json()

                    data["analysis"] = response_data

                # add the analysis result to the serializer data
                serializer.validated_data["analysis"] = data["analysis"]

                # Save the serializer data with the external analysis result
                await sync_to_async(serializer.save)()
                created_data.append(serializer.data)
    else:
        # do general analysis POST request
        response_data = None
        status_code = None
        url = "https://whisp.openforis.org/api/geojson"
        headers = {"Content-Type": "application/json"}
        body = data
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.post(url, headers=headers, json=body)
            response_data = response.json()
            status_code = response.status_code

        if status_code == 200:
            data = data['features']
            # Save the serializer data with the external analysis result
            for i, item in enumerate(response_data['data']):
                # check if geometry type is Polygon
                is_polygon = item['geometry']['type'] == 'Polygon' if 'geometry' in item else False
                serializer = EUDRFarmModelSerializer(
                    data=(
                        {
                            "farmer_name": data[i]["properties"].get("farmer_name", None),
                            "farm_size": data[i]["properties"].get("farm_size", item['Plot_area_ha']),
                            "collection_site": data[i]["properties"].get("collection_site", None),
                            "agent_name": data[i]["properties"].get("agent_name", None),
                            "farm_village": data[i]["properties"].get("farm_village", None),
                            "farm_district": data[i]["properties"].get("farm_district", item['Admin_Level_1']),
                            "latitude": data[i]["properties"].get("latitude", None) if not is_polygon else item['Centroid_lat'],
                            "longitude": data[i]["properties"].get("longitude", None) if not is_polygon else item['Centroid_lon'],
                            "polygon": data[i]["geometry"].get("coordinates", None),
                            "analysis":
                                {
                                    "is_in_protected_areas": item['WDPA'],
                                    "is_in_water_body": item['In_waterbody'],
                                    "forest_change_loss_after_2020": item['GFC_loss_after_2020'],
                                    "fire_after_2020": item['MODIS_fire_after_2020'],
                                    "radd_after_2020": item['RADD_after_2020'],
                                    "tmf_deforestation_after_2020": item['TMF_def_after_2020'],
                                    "tmf_degradation_after_2020": item['TMF_deg_after_2020'],
                                    "tmf_disturbed": item['TMF_disturbed'],
                                    "tree_colver_loss": item['Indicator_1_treecover'],
                                    "commodities": item['Indicator_2_commodities'],
                                    "disturbance_after_2020": item['Indicator_4_disturbance_after_2020'],
                                    "eudr_risk_level": item['EUDR_risk']
                            }
                        }
                    )
                )
                if serializer.is_valid():
                    await sync_to_async(serializer.save)()
                    created_data.append(serializer.data)
        else:
            errors.append({"error": serializer.errors})

    return errors, created_data


def transform_csv_to_json(data):
    features = []
    for record in data:
        if 'latitude' in record and 'longitude' in record and record['latitude'] and record['longitude']:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(record['longitude']), float(record['latitude'])]
                },
                "properties": {k: v for k, v in record.items() if k not in ['latitude', 'longitude', 'polygon']}
            }
            features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    return geojson


@api_view(["POST"])
def create_farm_data(request):
    data_format = request.data.get('format')
    raw_data = request.data.get(
        'data') if data_format == 'geojson' else transform_csv_to_json(request.data.get('data'))

    if not data_format or not raw_data:
        return Response({'error': 'Format and data are required'}, status=status.HTTP_400_BAD_REQUEST)

    if data_format == 'geojson' or data_format == 'csv':
        errors = validate_geojson(raw_data)
    else:
        return Response({'error': 'Unsupported format'}, status=status.HTTP_400_BAD_REQUEST)

    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    serializer = EUDRFarmModelSerializer(data=request.data)

    # combine file_name and format to save in the database with dummy uploaded_by. then retrieve the file_id
    file_data = {
        "file_name": f"{request.data.get('file_name')}.{request.data.get('format')}",
        "uploaded_by": request.user.username if request.user.is_authenticated else "admin",
    }
    file_serializer = EUDRUploadedFilesModelSerializer(data=file_data)

    if file_serializer.is_valid():
        if not EUDRUploadedFilesModel.objects.filter(file_name=file_data["file_name"]).exists():
            file_serializer.save()
        file_id = EUDRUploadedFilesModel.objects.get(
            file_name=file_data["file_name"]).id
    else:
        EUDRUploadedFilesModel.objects.get(
            id=file_serializer.data.get("id")).delete()
        return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Call the async function from sync context
    errors, created_data = async_to_sync(async_create_farm_data)(
        raw_data, serializer, file_id)
    if errors:
        # delete the file if there are errors
        EUDRUploadedFilesModel.objects.get(id=file_id).delete()
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    return Response(created_data, status=status.HTTP_201_CREATED)


@api_view(["PUT"])
def update_farm_data(request, pk):
    farm_data = EUDRFarmModel.objects.get(id=pk)
    serializer = EUDRFarmModelSerializer(instance=farm_data, data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def sync_farm_data(request):
    serializer = EUDRFarmModelSerializer(data=request.data)

    # combine file_name and format to save in the database with dummy uploaded_by. then retrieve the file_id
    file_data = {
        "file_name": f"{request.data[0].get('collection_site')}_{request.data[0].get("device_id")}.json",
        "device_id": request.data[0].get("device_id"),
        "uploaded_by": request.user.username if request.user.is_authenticated else "admin",
    }
    file_serializer = EUDRUploadedFilesModelSerializer(data=file_data)

    # read the data from the request, loop through the data, check if the record exists, if not, create the record,
    # if it exists, update the record
    data = request.data

    # loop through the data and check if the record exists
    for item in data:
        # check if data device_id exists in file table
        if not EUDRUploadedFilesModel.objects.filter(device_id=item["device_id"]).exists():
            # create a new file record
            if file_serializer.is_valid():
                file_serializer.save()
                file_id = file_serializer.data.get("id")
            else:
                EUDRUploadedFilesModel.objects.get(
                    id=file_serializer.data.get("id")).delete()
                return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            # update farm data with file_id corresponding to the device_id
            file_data = EUDRUploadedFilesModel.objects.get(
                device_id=item["device_id"])
            file_id = file_data.id
            # Call the async function from sync context
            errors, created_data = async_to_sync(async_create_farm_data)(
                item, serializer, file_id, True
            )

            if errors:
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)

            return Response(created_data, status=status.HTTP_201_CREATED)
        else:
            if file_serializer.is_valid():
                # Call the async function from sync context
                errors, created_data = async_to_sync(async_create_farm_data)(
                    item, serializer, file_serializer.data.get(
                        "id"), True
                )

            if errors:
                # delete the file if there are errors
                EUDRUploadedFilesModel.objects.get(id=file_id).delete()
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    return Response(created_data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def retrieve_farm_data(request):
    files = EUDRUploadedFilesModel.objects.filter(
        uploaded_by=request.user.username if request.user.is_authenticated else "admin"
    )
    filesSerializer = EUDRUploadedFilesModelSerializer(files, many=True)

    data = EUDRFarmModel.objects.filter(
        file_id__in=[file["id"] for file in filesSerializer.data]
    ).order_by("-updated_at")

    serializer = EUDRFarmModelSerializer(data, many=True)

    return Response(serializer.data)


@api_view(["GET"])
def retrieve_map_data(request):
    files = EUDRUploadedFilesModel.objects.all()
    filesSerializer = EUDRUploadedFilesModelSerializer(files, many=True)

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
    data = EUDRUploadedFilesModel.objects.filter(
        uploaded_by=request.user.username if request.user.is_authenticated else "admin"
    ).order_by("-updated_at")
    serializer = EUDRUploadedFilesModelSerializer(data, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def retrieve_file(request, pk):
    data = EUDRUploadedFilesModel.objects.get(id=pk)
    serializer = EUDRUploadedFilesModelSerializer(data, many=False)
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

    # GeoJSON format will depend on your specific data structure
    # This is just an example
    geojson_data = {"type": "FeatureCollection", "features": [
        {
            "type": "Feature",
            "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [41.8781, 87.6298],
                            [41.8781, 87.6299],
                        ]
                    ]
            },
            "properties": {
                "farmer_name": "John Doe",
                "farm_size": 4,
                "collection_site": "Site A",
                "farm_village": "Village A",
                "farm_district": "District A",
                "latitude": "-1.62883139933721",
                "longitude": "29.9898212498949",
            },
        }
    ]}

    if format == "csv":
        response = HttpResponse(content_type="text/csv")
        filename = f"eudr-upload-template-{timestamp_str}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        df.to_csv(response, index=True)
    elif format == "geojson":
        response = HttpResponse(content_type="application/json")
        filename = f"eudr-upload-template-{timestamp_str}.geojson"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write(json.dumps(geojson_data))
    else:
        return Response({"error": "Invalid format"}, status=status.HTTP_400_BAD_REQUEST)

    return response
