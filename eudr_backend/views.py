import ast
import json
from django.http import HttpResponse
from django.utils import timezone
import httpx
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

REQUIRED_FIELDS = [
    'farmer_name',
    'farm_size',
    'collection_site',
    'farm_district',
    'farm_village',
    'latitude',
    'longitude',
    'polygon',
]

OPTIONAL_FIELDS = [
    'remote_id',
    'member_id',
    'agent_name',
    'created_at',
    'updated_at',
]

GEOJSON_REQUIRED_FIELDS = ['geometry',
                           'farmer_name',
                           'farm_size',
                           'collection_site',
                           'farm_district',
                           'farm_village',
                           'latitude',
                           'longitude',
                           ]


def validate_csv(data):
    errors = []

    # Check if required fields are present
    for field in REQUIRED_FIELDS:
        if field not in data[0]:
            errors.append(f'"{field}" is required.')
    if len(errors) > 0:
        return errors

    # Check if optional fields are present
    for field in data[0]:
        if field not in REQUIRED_FIELDS and field not in OPTIONAL_FIELDS:
            errors.append(f'"{field}" is not a valid field.')
    if len(errors) > 0:
        return errors

    # Check if farm_size, latitude, and longitude are numbers and polygon is a list
    for i, record in enumerate(
        data[:-1] if (
            len(data[-1]) < len(REQUIRED_FIELDS)
        ) else data
    ):
        try:
            float(record['farm_size'])
        except ValueError:
            errors.append(f'Row {i}: "farm_size" must be a number.')
        try:
            float(record['latitude'])
        except ValueError:
            errors.append(f'Row {i}: "latitude" must be a number.')
        try:
            float(record['longitude'])
        except ValueError:
            errors.append(f'Row {i}: "longitude" must be a number.')
        try:
            ast.literal_eval(record['polygon'])
        except ValueError:
            errors.append(f'Row {i}: "polygon" must be a list.')
        except SyntaxError:
            errors.append(f'Row {i}: "polygon" must be a list.')

    return errors


def validate_geojson(data: dict) -> bool:
    errors = []

    if data.get('type') != 'FeatureCollection':
        errors.append('Invalid GeoJSON type. Must be FeatureCollection')
    if not isinstance(data.get('features'), list):
        errors.append('Invalid GeoJSON features. Must be a list')

    if len(errors) > 0:
        return errors

    for feature in data['features']:
        if feature.get('type') != 'Feature':
            errors.append('Invalid GeoJSON feature. Must be Feature')
            continue
        properties = feature.get('properties')
        if not isinstance(properties, dict):
            errors.append('Invalid GeoJSON properties. Must be a dictionary')
            continue

        # Check for required properties
        required_properties = {
            'farmer_name': str,
            'farm_village': str,
            'farm_district': str,
            'farm_size': (int, float),
            'latitude': (int, float),
            'longitude': (int, float),
        }
        for prop, prop_type in required_properties.items():
            if not isinstance(properties.get(prop), prop_type):
                errors.append(
                    f'Invalid GeoJSON properties. Missing or invalid "{prop}"')
        if len(errors) > 0:
            return errors

        # Check for valid geometry
        geometry = feature.get('geometry')
        if not isinstance(geometry, dict):
            errors.append('Invalid GeoJSON geometry. Must be a dictionary')
            continue
        geometry_type = geometry.get('type')
        coordinates = geometry.get('coordinates')

        if geometry_type == 'Polygon':
            if not (isinstance(coordinates, list) and len(coordinates) >= 1):
                errors.append(
                    'Invalid GeoJSON coordinates. Must be a list of lists')
            if not (isinstance(coordinates[0], list) and len(coordinates[0]) >= 4):
                errors.append(
                    'Invalid GeoJSON coordinates. Must be a list of lists with at least 4 coordinates')
            for coord in coordinates[0]:
                if not (isinstance(coord, list) and len(coord) == 2):
                    errors.append(
                        'Invalid GeoJSON coordinates. Must be a list of lists with 2 coordinates')
                if not all(isinstance(c, (int, float)) for c in coord):
                    errors.append(
                        'Invalid GeoJSON coordinates. Must be a list of lists with numbers')
        elif geometry_type == 'Point':
            if not (isinstance(coordinates, list) and len(coordinates) == 2):
                errors.append(
                    'Invalid GeoJSON coordinates. Must be a list of 2 numbers')
            if not all(isinstance(c, (int, float)) for c in coordinates):
                errors.append(
                    'Invalid GeoJSON coordinates. Must be a list of numbers')
        else:
            errors.append(
                'Invalid GeoJSON geometry type. Must be Point or Polygon')

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
                    chunk_size = 1000
                    analysis_results = []
                    features = data.get('features', [])

                    if not features:
                        return {"error": "No features found in the data."}
                    async with httpx.AsyncClient(timeout=1200.0) as client:
                        for i in range(0, len(features), chunk_size):
                            chunk = features[i:i + chunk_size]
                            chunked_data = {
                                # Preserve the GeoJSON structure
                                "type": data.get("type", "FeatureCollection"),
                                "features": chunk
                            }
                            response = await client.post(url, headers=headers, json=chunked_data)
                            response_data = response.json()
                            if (response.status_code != 200):
                                errors.append(
                                    {"error": "We encountered an issue on validating against global database,\n please try again later."})
                                return errors, created_data
                            analysis_results.extend(response_data['data'])
                            status_code = response.status_code

                    data["analysis"] = analysis_results

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
        chunk_size = 1000
        analysis_results = []
        features = data.get('features', [])

        if not features:
            return {"error": "No features found in the data."}
        async with httpx.AsyncClient(timeout=1200.0) as client:
            for i in range(0, len(features), chunk_size):
                chunk = features[i:i + chunk_size]
                chunked_data = {
                    # Preserve the GeoJSON structure
                    "type": data.get("type", "FeatureCollection"),
                    "features": chunk
                }
                response = await client.post(url, headers=headers, json=chunked_data)
                response_data = response.json()
                if (response.status_code != 200):
                    errors.append(
                        {"error": "We encountered an issue on validating against global database,\n please try again later."})
                    return errors, created_data
                analysis_results.extend(response_data['data'])
                status_code = response.status_code
            response_data = analysis_results

        if status_code == 200:
            data = data['features']
            # Save the serializer data with the external analysis result
            for i, item in enumerate(response_data):
                # check if geometry type is Polygon
                is_polygon = item.get('geometry', None), [
                    'type'] == 'Polygon' if 'geometry' in item else False
                serializer = EUDRFarmModelSerializer(
                    data=(
                        {
                            "farmer_name": data[i]["properties"].get("farmer_name", None),
                            "farm_size": float(data[i]["properties"].get("farm_size", item.get('Plot_area_ha', None))),
                            "collection_site": data[i]["properties"].get("collection_site", None),
                            "agent_name": data[i]["properties"].get("agent_name", None),
                            "farm_village": data[i]["properties"].get("farm_village", None),
                            "farm_district": data[i]["properties"].get("farm_district", item.get('Admin_Level_1', None)),
                            "file_id": file_id,
                            "latitude": data[i]["geometry"]['coordinates'][1] if not is_polygon else item.get('Centroid_lat', 0.0),
                            "longitude": data[i]["geometry"]['coordinates'][1] if not is_polygon else item.get('Centroid_lon', 0.0),
                            "polygon": data[i]["geometry"].get("coordinates", None),
                            "geoid": item.get("geoid", None),
                            "analysis":
                                {
                                    "is_in_protected_areas": item.get('WDPA', None),
                                    "is_in_water_body": item.get('In_waterbody', None),
                                    "forest_change_loss_after_2020": item.get('GFC_loss_after_2020', None),
                                    "fire_after_2020": item.get('MODIS_fire_after_2020', None),
                                    "radd_after_2020": item.get('RADD_after_2020', None),
                                    "tmf_deforestation_after_2020": item.get('TMF_def_after_2020', None),
                                    "tmf_degradation_after_2020": item.get('TMF_deg_after_2020', None),
                                    "tmf_disturbed": item.get('TMF_disturbed', None),
                                    "tree_cover_loss": item.get('Indicator_1_treecover', None),
                                    "commodities": item.get('Indicator_2_commodities', None),
                                    "disturbance_after_2020": item.get('Indicator_4_disturbance_after_2020', None),
                                    "eudr_risk_level": item.get('EUDR_risk', None)
                            }
                        }
                    )
                )
                if serializer.is_valid():
                    await sync_to_async(serializer.save)()
                    created_data.append(serializer.data)
                else:
                    errors.append({"error": serializer.errors})
        else:
            errors.append(
                {"error": "We encountered an issue on validating against global database,\n please try again later."})
    return errors, created_data


def transform_csv_to_json(data):
    features = []
    for record in data:
        # check if latitude, longitude, and polygon fields are not found in the record, skip the record
        if 'latitude' not in record or 'longitude' not in record:
            continue
        # check if polygon field is empty array or empty string
        if record.get('polygon') in ['[]', '']:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(record['longitude']), float(record['latitude'])]
                },
                "properties": {k: v for k, v in record.items() if k not in ['latitude', 'longitude', 'polygon']}
            }
            features.append(feature)
        else:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [ast.literal_eval(record.get('polygon', '[]'))]
                },
                "properties": {k: v for k, v in record.items() if k not in ['latitude', 'longitude', 'polygon']}
            }
            features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    return geojson


def transform_db_data_to_geojson(data):
    features = []
    for record in data:
        # check if latitude, longitude, and polygon fields are not found in the record, skip the record
        if 'latitude' not in record or 'longitude' not in record:
            continue
        # check if polygon field is empty array or empty string
        if record.get('polygon') in ['[]', '']:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(record['longitude']), float(record['latitude'])]
                },
                "properties": {k: v for k, v in record.items() if k not in ['latitude', 'longitude', 'polygon']}
            }
            features.append(feature)
        else:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [ast.literal_eval(record.get('polygon', '[]'))]
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
    raw_data = request.data.get('data')

    if not data_format or not raw_data:
        return Response({'error': 'Format and data are required'}, status=status.HTTP_400_BAD_REQUEST)
    elif data_format == 'geojson':
        errors = validate_geojson(raw_data)
    elif data_format == 'csv':
        errors = validate_csv(raw_data)
    else:
        return Response({'error': 'Unsupported format'}, status=status.HTTP_400_BAD_REQUEST)

    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    raw_data = request.data.get(
        'data') if data_format == 'geojson' else transform_csv_to_json(raw_data)

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


@api_view(["POST"])
def revalidate_farm_data(request):
    # get all the data belonging to authenticated user and send it to the external API for revalidation
    files = EUDRUploadedFilesModel.objects.filter(
        uploaded_by=request.user.username if request.user.is_authenticated else "admin"
    )
    filesSerializer = EUDRUploadedFilesModelSerializer(files, many=True)

    # get all the data belonging to the file_ids
    data = EUDRFarmModel.objects.filter(
        file_id__in=[file["id"] for file in filesSerializer.data]
    ).order_by("-updated_at")
    serializer = EUDRFarmModelSerializer(data, many=True)

    # format the data to geojson format and send to whisp API for processing
    raw_data = transform_db_data_to_geojson(serializer.data)

    # categorize the data with same file_id and send to the external API for revalidation, store result until all file_ids are processed
    serializer = EUDRFarmModelSerializer(data=request.data)

    # combine file_name and format to save in the database with dummy uploaded_by. then retrieve the file_id

    errors, created_data = async_to_sync(async_create_farm_data)(
        raw_data, serializer, 1)
    if errors:
        # delete the file if there are errors
        EUDRUploadedFilesModel.objects.get(id=1).delete()
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
        filename = f"terratrac-upload-template-{timestamp_str}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        df.to_csv(response, index=False)
    elif format == "geojson":
        response = HttpResponse(content_type="application/json")
        filename = f"terratrac-upload-template-{timestamp_str}.geojson"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write(json.dumps(geojson_data))
    else:
        return Response({"error": "Invalid format"}, status=status.HTTP_400_BAD_REQUEST)

    return response
