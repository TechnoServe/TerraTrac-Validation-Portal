import ast
import csv
import io
import json
import ee
from django.http import HttpResponse
from django.utils import timezone
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
            elif properties.get(field) in [None, '']:
                errors.append(f"""Feature {i}: "{
                              field}" is required and cannot be empty.""")

    return errors


def validate_json(data):
    errors = []

    for i, item in enumerate(data):
        for field in REQUIRED_FIELDS:
            if field not in item or item[field] in [None, '']:
                errors.append(
                    f'Item {i}: "{field}" is required and cannot be empty.')

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
async def async_create_farm_data(data, serializer, file_id, format, isSyncing=False):
    errors = []
    created_data = []
    initialize_earth_engine()

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
                    # url = "https://whisp.openforis.org/api/wkt"
                    # headers = {"Content-Type": "application/json"}
                    # body = {
                    #     "wkt": "POLYGON(("
                    #     + ",".join(f"{lon} {lat}" for lon, lat in coordinates)
                    #     + "))",
                    # }
                    # async with httpx.AsyncClient(timeout=60.0) as client:
                    #     response = await client.post(url, headers=headers, json=body)
                    #     response_data = response.json()

                    # tree cover loss after 2020
                    # tcl_url = "https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss/latest/query"
                    # tcl_headers = {"Content-Type": "application/json"}
                    # tcl_body = {
                    #     "geometry": {
                    #         "type": "Polygon",
                    #         "coordinates": [coordinates],
                    #     },
                    #     "sql": "SELECT SUM(area__ha) FROM results WHERE umd_tree_cover_loss__year > 2020"
                    # }
                    # async with httpx.AsyncClient(timeout=60.0) as client:
                    #     tcl_response = await client.post(tcl_url, json=tcl_body)
                    #     tcl_response_data = tcl_response.json()

                    # if response_data["status"] == "success":
                    #     response_data["data"]["tree_cover_loss_after_2020"] = tcl_response_data["data"][0]["area__ha"]

                    data["analysis"] = response_data

                # add the analysis result to the serializer data
                serializer.validated_data["analysis"] = data["analysis"]

                # Save the serializer data with the external analysis result
                await sync_to_async(serializer.save)()
                created_data.append(serializer.data)
    else:
        farm_data = data[0]["data"]["features"] if format == "geojson" else data[0]["data"]
        image2023 = ee.Image(
            'UMD/hansen/global_forest_change_2023_v1_11').select('lossyear').eq(1).selfMask()
        shapely_polygons = []

        for item in farm_data:
            # Add deforestation layer (2021-2023)
            deforestation = image2023
            # Fetch protected areas
            protected_areas = ee.FeatureCollection(
                "WCMC/WDPA/current/polygons")
            response_data = None

            # loop through the data and update the analysis field with the external analysis result
            polygon = item["geometry"]["coordinates"][0]
            print(polygon)
            if polygon:
                shapely_polygon = Polygon(polygon)

                # Check for overlap with existing polygons
                overlap = any(shapely_polygon.intersects(existing_polygon)
                              for existing_polygon in shapely_polygons)
                farm_feature = ee.Feature(
                    ee.Geometry.Polygon(polygon))
                intersecting_areas = protected_areas.filterBounds(
                    farm_feature.geometry())
                # Check if the farm intersects with deforestation areas
                intersecting_deforestation = deforestation.reduceRegions(collection=ee.FeatureCollection(
                    [farm_feature]), reducer=ee.Reducer.anyNonZero(), scale=30).first().get('any').getInfo()

                if intersecting_deforestation or intersecting_areas.size().getInfo() > 0:
                    response_data = {
                        'deforestation':
                            True if intersecting_deforestation else False,
                        'protected_areas': intersecting_areas.size().getInfo() > 0 or False,
                        'overlaps': overlap
                    }
                else:
                    response_data = {
                        'deforestation': False,
                        'protected_areas': False,
                        'overlaps': overlap
                    }

                shapely_polygons.append(shapely_polygon)
            else:
                shapely_polygon = Point(
                    [item["properties"]['longitude'], item["properties"]['latitude']])

                # Check for overlap with existing polygons
                overlap = any(shapely_polygon.intersects(existing_polygon)
                              for existing_polygon in shapely_polygons)
                shapely_polygons.append(shapely_polygon)
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
                        "analysis": response_data if response_data else None,
                    }
                    if format == "geojson"
                    else item
                )
            )
            # if farmer_name is empty, skip the record
            if not (
                item["properties"]["farmer_name"]
                if format == "geojson"
                else item["farmer_name"]
            ):
                continue

            # Check if a similar record already exists for each item
            if await EUDRFarmModel.objects.filter(
                farmer_name=(
                    item["properties"]["farmer_name"]
                    if format == "geojson"
                    else item["farmer_name"]
                ),
            ).aexists():
                continue
            elif serializer.is_valid():
                # add the file_id to the serializer data
                serializer.validated_data["file_id"] = file_id
                if (
                    len(
                        item["geometry"]["coordinates"][0][0]
                        if format == "geojson"
                        else ast.literal_eval(item["polygon"])
                    )
                    <= 1
                ):
                    item["analysis"] = None
                else:
                    # do general analysis POST request
                    response_data = None
                    # url = "https://whisp.openforis.org/api/wkt"
                    # headers = {"Content-Type": "application/json"}
                    # body = {
                    #     "wkt": "POLYGON(("
                    #     + ",".join(f"{lon} {lat}" for lon, lat in coordinates)
                    #     + "))",
                    # }
                    # async with httpx.AsyncClient(timeout=60.0) as client:
                    #     response = await client.post(url, headers=headers, json=body)
                    #     response_data = response.json()

                    # tree cover loss after 2020
                    # tcl_url = "https://data-api.globalforestwatch.org/dataset/umd_tree_cover_loss/latest/query"
                    # tcl_headers = {"Content-Type": "application/json"}
                    # tcl_body = {
                    #     "geometry": {
                    #         "type": "Polygon",
                    #         "coordinates": [coordinates],
                    #     },
                    #     "sql": "SELECT SUM(area__ha) FROM results WHERE umd_tree_cover_loss__year > 2020"
                    # }
                    # async with httpx.AsyncClient(timeout=60.0) as client:
                    #     tcl_response = await client.post(tcl_url, json=tcl_body)
                    #     tcl_response_data = tcl_response.json()

                    # if response_data["status"] == "success":
                    #     response_data["data"]["tree_cover_loss_after_2020"] = tcl_response_data["data"][0]["area__ha"]

                # Save the serializer data with the external analysis result
                await sync_to_async(serializer.save)()
                created_data.append(serializer.data)
            else:
                # delete the file if the serializer is not valid
                # if file_id:
                #     EUDRUploadedFilesModel.objects.get(id=file_id).delete()

                errors.append({"error": serializer.errors, "data": item})

    return errors, created_data


@api_view(["POST"])
def create_farm_data(request):
    data_format = request.data.get('format')
    raw_data = request.data.get('data')
    print(raw_data)

    if not data_format or not raw_data:
        return Response({'error': 'Format and data are required'}, status=status.HTTP_400_BAD_REQUEST)

    if data_format == 'geojson':
        errors = validate_geojson(raw_data)
    elif data_format == 'json':
        errors = validate_json(raw_data)
    elif data_format == 'csv':
        errors = validate_csv(raw_data)
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
        file_serializer.save()
        file_id = file_serializer.data.get("id")
    else:
        EUDRUploadedFilesModel.objects.get(
            id=file_serializer.data.get("id")).delete()
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
                item, serializer, file_id, "geojson", True
            )

            if errors:
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)

            return Response(created_data, status=status.HTTP_201_CREATED)
        else:
            if file_serializer.is_valid():
                # Call the async function from sync context
                errors, created_data = async_to_sync(async_create_farm_data)(
                    item, serializer, file_serializer.data.get(
                        "id"), "geojson", True
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

    if format == "csv":
        response = HttpResponse(content_type="text/csv")
        filename = f"eudr-upload-template-{timestamp_str}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        df.to_csv(response, index=True)
    elif format == "json":
        response = HttpResponse(content_type="application/json")
        filename = f"eudr-upload-template-{timestamp_str}.json"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        df.to_json(response, orient="records")
    elif format == "geojson":
        response = HttpResponse(content_type="application/json")
        filename = f"eudr-upload-template-{timestamp_str}.geojson"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
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
        response.write(json.dumps(geojson_data))
    else:
        return Response({"error": "Invalid format"}, status=status.HTTP_400_BAD_REQUEST)

    return response
