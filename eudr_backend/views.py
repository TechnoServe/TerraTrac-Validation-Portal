import ast
import json
from django.http import HttpResponse
from django.utils import timezone
from django.core.cache import cache
import httpx
import pandas as pd
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from asgiref.sync import async_to_sync, sync_to_async
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordResetView
import boto3
from shapely import MultiPolygon, Polygon, unary_union

from eudr_backend import settings
from eudr_backend.models import EUDRCollectionSiteModel, EUDRFarmBackupModel, EUDRSharedMapAccessCodeModel, WhispAPISetting, EUDRFarmModel, EUDRUploadedFilesModel, EUDRUserModel
from eudr_backend.tasks import update_geoid
from datetime import timedelta
import uuid
from .serializers import (
    EUDRCollectionSiteModelSerializer,
    EUDRFarmBackupModelSerializer,
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
    'polygon'
]

OPTIONAL_FIELDS = [
    'remote_id',
    'member_id',
    'agent_name',
    'created_at',
    'updated_at',
    'accuracyArray',
    'accuracies'
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
            errors.append(f'Record {i+1}: "farm_size" must be a number.')
        try:
            float(record['latitude'])
        except ValueError:
            errors.append(f'Record {i+1}: "latitude" must be a number.')
        try:
            float(record['longitude'])
        except ValueError:
            errors.append(f'Record {i+1}: "longitude" must be a number.')

    # if polygon is invalid, return error
    for i, record in enumerate(
        data[:-1] if (
            len(data[-1]) < len(REQUIRED_FIELDS)
        ) else data
    ):
        try:
            polygon = record['polygon']
            if float(record['farm_size']) >= 4 and not is_valid_polygon(json.loads(polygon)):
                errors.append(
                    f'Record {i+1}: Should have valid polygon format.')
            elif polygon and not is_valid_polygon(json.loads(polygon)):
                errors.append(
                    f'Record {i+1}: Should have valid polygon format.')
        except ValueError:
            errors.append(f'Record {i+1}: "polygon" must be a list.')
        except SyntaxError:
            errors.append(f'Record {i+1}: "polygon" must be a list.')

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
            print(geometry)
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
            if properties.get('farm_size') >= 4 and not is_valid_polygon(coordinates):
                errors.append(
                    'Invalid GeoJSON coordinates. Must be a valid polygon')
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
            if properties.get('farm_size') >= 4:
                errors.append(
                    'Invalid record. Farm size must be less than 4 hectares for a point geometry')
        elif geometry_type == 'MultiPolygon':
            if not (isinstance(coordinates, list) and len(coordinates) >= 1):
                errors.append(
                    'Invalid GeoJSON coordinates. Must be a list of lists')
            for polygon in coordinates:
                if not (isinstance(polygon, list) and len(polygon) >= 1):
                    errors.append(
                        'Invalid GeoJSON coordinates. Must be a list of lists')
                if not (isinstance(polygon[0], list) and len(polygon[0]) >= 4):
                    errors.append(
                        'Invalid GeoJSON coordinates. Must be a list of lists with at least 4 coordinates')
                if properties.get('farm_size') >= 4 and not is_valid_polygon(polygon):
                    errors.append(
                        'Invalid GeoJSON coordinates. Must be a valid polygon')
                for coord in polygon[0]:
                    if not (isinstance(coord, list) and len(coord) == 2):
                        errors.append(
                            'Invalid GeoJSON coordinates. Must be a list of lists with 2 coordinates')
                    if not all(isinstance(c, (int, float)) for c in coord):
                        errors.append(
                            'Invalid GeoJSON coordinates. Must be a list of lists with numbers')
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
    data = User.objects.all().order_by("-date_joined")
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
async def async_create_farm_data(data, serializer, file_id, isSyncing=False, hasCreatedFiles=[]):
    cache.delete('high_risk_layer')
    cache.delete('low_risk_layer')
    cache.delete('more_info_needed_layer')

    errors = []
    created_data = []

    if isSyncing:
        formatted_data = transform_db_data_to_geojson(data, True)
        err, analysis_results = await perform_analysis(formatted_data, hasCreatedFiles)
        if err:
            errors.append(err)
        else:
            err, new_data = await save_farm_data(formatted_data, file_id, analysis_results)
            if err:
                errors.append(err)
            else:
                created_data.append(new_data)

        return errors, created_data
    else:
        err, analysis_results = await perform_analysis(data)
        if err:
            # delete the file if there are errors
            EUDRUploadedFilesModel.objects.get(id=file_id).delete()
            errors.append(err)
        else:
            err, new_data = await save_farm_data(data, file_id, analysis_results)
            if err:
                # delete the file if there are errors
                EUDRUploadedFilesModel.objects.get(id=file_id).delete()
                errors.append(err)
            else:
                created_data.extend(new_data)
    serializerData = EUDRFarmModelSerializer(created_data, many=True)

    return errors, serializerData.data


async def get_existing_record(data):
    # Define your lookup fields
    lookup_fields = {
        'farmer_name': data.get('farmer_name'),
        'latitude': data.get('latitude'),
        'longitude': data.get('longitude'),
        'polygon': data.get('polygon'),
        'collection_site': data.get('collection_site'),
    }
    # Check if a record exists with these fields
    return await sync_to_async(EUDRFarmModel.objects.filter(**lookup_fields).first)()


async def perform_analysis(data, hasCreatedFiles=[]):
    url = "https://whisp.openforis.org/api/geojson"
    headers = {"Content-Type": "application/json"}
    settings = await sync_to_async(WhispAPISetting.objects.first)()
    chunk_size = settings.chunk_size if settings else 500
    analysis_results = []
    data = json.loads(data) if isinstance(data, str) else data
    data = flatten_geojson(data)
    features = data.get('features', [])

    if not features:
        return {"error": "No features found in the data."}, None

    async with httpx.AsyncClient(timeout=1200.0) as client:
        for i in range(0, len(features), chunk_size):
            chunk = features[i:i + chunk_size]
            chunked_data = {
                "type": data.get("type", "FeatureCollection"),
                "features": chunk
            }
            response = await client.post(url, headers=headers, json=chunked_data)

            if response.status_code != 200:
                if hasCreatedFiles:
                    EUDRUploadedFilesModel.objects.filter(
                        id__in=hasCreatedFiles).delete()
                return {"Validation against global database failed."}, None
            analysis_results.extend(response.json().get('data', []))

    return None, analysis_results


async def save_farm_data(data, file_id, analysis_results=None):
    formatted_data = format_geojson_data(data, analysis_results, file_id)
    saved_records = []

    for item in formatted_data:
        query = Q(farmer_name=item['farmer_name'],
                  collection_site=item['collection_site'])

        # Additional condition if polygon exists
        if item.get('polygon'):
            query &= Q(polygon__isnull=False) & ~Q(polygon=[])

        # Additional condition if latitude and longitude are not 0 or 0.0
        if item.get('latitude', 0) != 0 or item.get('longitude', 0) != 0:
            query &= (Q(latitude=item['latitude'])
                      | Q(longitude=item['longitude']))

        # Retrieve the existing record based on the constructed query
        existing_record = await sync_to_async(EUDRFarmModel.objects.filter(query).first)()

        if existing_record:
            serializer = EUDRFarmModelSerializer(
                existing_record, data=item)
        else:
            serializer = EUDRFarmModelSerializer(data=item)

        if serializer.is_valid():
            saved_instance = await sync_to_async(serializer.save)()
            saved_records.append(saved_instance)
        else:
            # delete the file if there are errors
            EUDRUploadedFilesModel.objects.get(id=file_id).delete()
            return serializer.errors, None

    return None, saved_records


def format_geojson_data(geojson, analysis, file_id=None):
    # Ensure the GeoJSON contains features
    geojson = json.loads(geojson) if isinstance(geojson, str) else geojson
    features = geojson.get('features', [])
    if not features:
        return []

    formatted_data_list = []
    for i, feature in enumerate(features):
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})

        # Determine if the geometry is a Polygon and extract coordinates
        is_polygon = geometry.get('type') == 'Polygon' or geometry.get(
            'type') == 'MultiPolygon'
        coordinates = geometry.get('coordinates', [])

        # make union of coordinates if it is a MultiPolygon
        if geometry.get('type') == 'MultiPolygon':
            coordinates = []
            for polygon in geometry.get('coordinates', []):
                coordinates.extend(polygon)
        else:
            coordinates = geometry.get('coordinates', [])

        latitude = coordinates[1] if not is_polygon and len(
            coordinates) > 1 else properties.get('Centroid_lat', 0.0)
        longitude = coordinates[0] if not is_polygon and len(
            coordinates) > 0 else properties.get('Centroid_lon', 0.0)
        formatted_data = {
            "remote_id": properties.get("remote_id"),
            "farmer_name": properties.get("farmer_name"),
            "farm_size": float(properties.get("farm_size", properties.get('Plot_area_ha', 0))),
            "collection_site": properties.get("collection_site"),
            "agent_name": properties.get("agent_name"),
            "farm_village": properties.get("farm_village"),
            "farm_district": properties.get("farm_district", properties.get('Admin_Level_1')),
            "latitude": latitude,
            "longitude": longitude,
            "polygon": coordinates,
            "polygon_type": geometry.get('type'),
            "geoid": properties.get("geoid"),
            "file_id": file_id,
            "analysis": {
                "is_in_protected_areas": analysis[i].get('WDPA'),
                "is_in_water_body": analysis[i].get('In_waterbody'),
                "forest_change_loss_after_2020": analysis[i].get('GFC_loss_after_2020'),
                "fire_after_2020": analysis[i].get('MODIS_fire_after_2020'),
                "radd_after_2020": analysis[i].get('RADD_after_2020'),
                "tmf_deforestation_after_2020": analysis[i].get('TMF_def_after_2020'),
                "tmf_degradation_after_2020": analysis[i].get('TMF_deg_after_2020'),
                "tmf_disturbed": analysis[i].get('TMF_disturbed'),
                "tree_cover_loss": analysis[i].get('Indicator_1_treecover'),
                "commodities": analysis[i].get('Indicator_2_commodities'),
                "disturbance_before_2020": analysis[i].get('Indicator_3_disturbance_before_2020'),
                "disturbance_after_2020": analysis[i].get('Indicator_4_disturbance_after_2020'),
                "eudr_risk_level": analysis[i].get('EUDR_risk')
            }
        }
        formatted_data_list.append(formatted_data)

    return formatted_data_list


def is_valid_polygon(polygon):
    # Check if the polygon is a list and has at least 3 points, each with exactly 2 coordinates
    try:
        if isinstance(polygon, list) and (
            (len(polygon[0]) >= 3 or len(polygon) >= 3) or
            (isinstance(polygon[0], list) and len(polygon[0][0]) >= 3)
        ):
            return True
        return False
    except Exception as e:
        return False


def transform_csv_to_json(data):
    features = []
    for record in data:
        # check if latitude, longitude, and polygon fields are not found in the record, skip the record
        if 'latitude' not in record or 'longitude' not in record:
            continue
        # check if polygon field is empty array or empty string
        if not record.get('polygon') or record.get('polygon') in ['']:
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


def flatten_geojson(geojson):
    """
    Loops through a GeoJSON object and flattens any MultiPolygon geometry to Polygon.
    """
    for feature in geojson.get('features', []):
        geometry = feature.get('geometry', {})
        if geometry['type'] == 'MultiPolygon':
            # Flatten the MultiPolygon into a Polygon
            feature['geometry'] = flatten_multipolygon(geometry)
    return geojson


def flatten_multipolygon(multipolygon):
    """
    Flattens a MultiPolygon geometry into a Polygon by combining inner arrays of coordinates.
    """
    if multipolygon['type'] != 'MultiPolygon':
        raise ValueError("Input geometry is not a MultiPolygon")

    # Initialize an empty list to hold combined coordinates
    flattened_coordinates = []

    # Iterate through the coordinates of each polygon in the MultiPolygon
    for polygon in multipolygon['coordinates']:
        # Each polygon has a list of rings (outer boundary, inner holes), we only want to combine the outer boundaries
        for ring in polygon:
            flattened_coordinates.extend(ring)

    # Create the new Polygon geometry
    polygon = {
        "type": "Polygon",
        "coordinates": [flattened_coordinates]
    }

    return polygon


def flatten_multipolygon_coordinates(multipolygon_coords):
    flattened_coordinates = []
    for polygon in multipolygon_coords:
        flattened_coordinates.extend(polygon)
    return [flattened_coordinates]


def transform_db_data_to_geojson(data, isSyncing=False):
    features = []
    for record in data:
        # check if latitude, longitude, and polygon fields are not found in the record, skip the record
        if 'latitude' not in record or 'longitude' not in record:
            continue
        if not record.get('polygon') or record.get('polygon') in [''] or ((len(record.get('polygon', [])) == 1 and not isinstance(record.get('polygon', [])[0], list))):
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
                    "coordinates": ast.literal_eval(record.get('polygon', '[]')) if type(record.get('polygon', '[]')) == str else record.get('polygon', '[]')
                },
                "properties": {k: v for k, v in record.items() if k not in ['latitude', 'longitude', 'polygon']}
            }
            features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
        "generateGeoids": "true" if isSyncing else "false"
    }

    return geojson


@api_view(["POST"])
def create_farm_data(request):
    cache.delete('high_risk_layer')
    cache.delete('low_risk_layer')
    cache.delete('more_info_needed_layer')

    data_format = request.data.get('format')
    raw_data = json.loads(request.data.get(
        'data')) if isinstance(request.data.get('data'), str) else request.data.get('data')
    file = request.FILES.get('file')
    file_name = file.name.split('.')[0]

    if not data_format or not raw_data:
        return Response({'error': 'Format and data are required'}, status=status.HTTP_400_BAD_REQUEST)
    elif data_format == 'geojson':
        errors = validate_geojson(raw_data)
    elif data_format == 'csv':
        errors = validate_csv(raw_data)
    else:
        return Response({'error': 'Unsupported format'}, status=status.HTTP_400_BAD_REQUEST)

    if errors:
        # store the file in aws s3 bucket failed directory
        s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        s3.upload_fileobj(file, settings.AWS_STORAGE_BUCKET_NAME,
                          f'failed/{request.user.username}_{file.name}', ExtraArgs={'ACL': 'public-read'})
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    raw_data = request.data.get(
        'data') if data_format == 'geojson' else transform_csv_to_json(raw_data)

    serializer = EUDRFarmModelSerializer(data=request.data)

    # combine file_name and format to save in the database with dummy uploaded_by. then retrieve the file_id
    file_data = {
        "file_name": f"{file_name}.{request.data.get('format')}",
        "uploaded_by": request.user.username if request.user.is_authenticated else "admin",
    }
    file_serializer = EUDRUploadedFilesModelSerializer(data=file_data)

    if file_serializer.is_valid():
        if not EUDRUploadedFilesModel.objects.filter(file_name=file_data["file_name"], uploaded_by=request.user.username if request.user.is_authenticated else "admin").exists():
            file_serializer.save()
        file_id = EUDRUploadedFilesModel.objects.get(
            file_name=file_data["file_name"], uploaded_by=request.user.username if request.user.is_authenticated else "admin").id
    else:
        EUDRUploadedFilesModel.objects.get(
            id=file_serializer.data.get("id")).delete()
        # store the file in aws s3 bucket failed directory
        s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        s3.upload_fileobj(file, settings.AWS_STORAGE_BUCKET_NAME,
                          f'failed/{request.user.username}_{file.name}', ExtraArgs={'ACL': 'public-read'})
        return Response({'errors': file_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    # Call the async function from sync context
    errors, created_data = async_to_sync(async_create_farm_data)(
        raw_data, serializer, file_id)
    if errors:
        # delete the file if there are errors
        EUDRUploadedFilesModel.objects.get(id=file_id).delete()
        # store the file in aws s3 bucket failed directory
        s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                          aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        s3.upload_fileobj(file, settings.AWS_STORAGE_BUCKET_NAME,
                          f'failed/{request.user.username}_{file.name}', ExtraArgs={'ACL': 'public-read'})
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    update_geoid(repeat=60,
                 user_id=request.user.username if request.user.is_authenticated else "admin")

    # store the file in aws s3 bucket processed directory
    s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
    s3.upload_fileobj(file, settings.AWS_STORAGE_BUCKET_NAME,
                      f'processed/{request.user.username}_{file.name}', ExtraArgs={'ACL': 'public-read'})
    return Response(created_data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def sync_farm_data(request):
    sync_results = []
    data = request.data
    for entry in data:
        # Check or create collection site
        site_data = entry.get('collection_site')
        # append device_id to site_data
        site_data['device_id'] = entry.get("device_id")
        site, created = EUDRCollectionSiteModel.objects.update_or_create(
            name=site_data['name'],
            defaults=site_data
        )

        # Sync farms
        for farm_data in entry.get('farms', []):
            farm_data['site_id'] = site
            farm, farm_created = EUDRFarmBackupModel.objects.update_or_create(
                remote_id=farm_data.get('remote_id'),
                defaults=farm_data
            )
            sync_results.append(farm.remote_id)

    return Response({"synced_remote_ids": sync_results}, status=status.HTTP_200_OK)


@api_view(["POST"])
def restore_farm_data(request):
    device_id = request.data.get("device_id")
    phone_number = request.data.get("phone_number")
    email = request.data.get("email")

    collection_sites = []

    # Query based on priority: device_id, phone_number, or email
    if device_id:
        collection_sites = EUDRCollectionSiteModel.objects.filter(
            device_id=device_id)
    elif phone_number:
        collection_sites = EUDRCollectionSiteModel.objects.filter(
            phone_number=phone_number)
    elif email:
        collection_sites = EUDRCollectionSiteModel.objects.filter(email=email)

    if not collection_sites:
        return Response([], status=status.HTTP_200_OK)

    # Prepare the restore data in the required format
    restore_data = []

    for site in collection_sites:
        # Fetch all farms linked to this collection site
        farms = EUDRFarmBackupModel.objects.filter(site_id=site.id)
        farm_data = EUDRFarmBackupModelSerializer(farms, many=True).data

        # Construct the structure with the collection site and farms
        restore_data.append({
            "device_id": site.device_id,
            "collection_site": EUDRCollectionSiteModelSerializer(site).data,
            "farms": farm_data
        })

    return Response(restore_data, status=status.HTTP_200_OK)


@api_view(["PUT"])
def update_farm_data(request, pk):
    cache.delete('high_risk_layer')
    cache.delete('low_risk_layer')
    cache.delete('more_info_needed_layer')
    farm_data = EUDRFarmModel.objects.get(id=pk)
    serializer = EUDRFarmModelSerializer(instance=farm_data, data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def revalidate_farm_data(request, pk):
    # get all the data belonging to the file_ids
    data = EUDRFarmModel.objects.filter(
        file_id=pk
    ).order_by("-updated_at")
    serializer = EUDRFarmModelSerializer(data, many=True)

    # format the data to geojson format and send to whisp API for processing
    raw_data = transform_db_data_to_geojson(serializer.data)

    # combine file_name and format to save in the database with dummy uploaded_by. then retrieve the file_id

    errors, created_data = async_to_sync(async_create_farm_data)(
        raw_data, serializer, pk)
    if errors:
        # delete the file if there are errors
        EUDRUploadedFilesModel.objects.get(id=pk).delete()
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    return Response(created_data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def retrieve_farm_data(request):
    files = EUDRUploadedFilesModel.objects.filter(
        uploaded_by=request.user.username if request.user.is_authenticated else "admin"
    ) if not request.user.is_staff else EUDRUploadedFilesModel.objects.all()
    filesSerializer = EUDRUploadedFilesModelSerializer(files, many=True)

    data = EUDRFarmModel.objects.filter(
        file_id__in=[file["id"] for file in filesSerializer.data]
    ).order_by("-updated_at")

    serializer = EUDRFarmModelSerializer(data, many=True)

    return Response(serializer.data)


@api_view(["GET"])
def retrieve_overlapping_farm_data(request, pk):
    files = EUDRUploadedFilesModel.objects.filter(
        id=pk) if not request.user.is_staff else EUDRUploadedFilesModel.objects.all()

    filesSerializer = EUDRUploadedFilesModelSerializer(files, many=True)

    farms = EUDRFarmModel.objects.filter(
        file_id=filesSerializer.data[0].get("id")
    ).order_by("-updated_at")

    farmSerializer = EUDRFarmModelSerializer(farms, many=True)

    overLaps = []
    farms = farmSerializer.data

    for farm in farms:
        # Assuming farm data has 'farmer_name', 'latitude', 'longitude', 'farm_size', and 'polygon' fields
        polygon = flatten_multipolygon_coordinates(
            farm['polygon']) if farm['polygon_type'] == 'MultiPolygon' else farm['polygon']
        if 'polygon' in farm and len(polygon) == 1:
            polygon = flatten_multipolygon_coordinates(farm['polygon'])

            if polygon:
                farm_polygon = Polygon(polygon[0])
                is_overlapping = any(farm_polygon.overlaps(
                    Polygon(other_farm['polygon'][0])) for other_farm in farms)
                overLaps.append(farm) if is_overlapping else None

    return Response(overLaps)


@api_view(["GET"])
def retrieve_user_farm_data(request, pk):
    users = User.objects.filter(id=pk)
    files = EUDRUploadedFilesModel.objects.filter(
        uploaded_by=users.values()[0].get("username")
    )
    filesSerializer = EUDRUploadedFilesModelSerializer(files, many=True)

    data = EUDRFarmModel.objects.filter(
        file_id__in=[file["id"] for file in filesSerializer.data]
    ).order_by("-updated_at")

    serializer = EUDRFarmModelSerializer(data, many=True)

    return Response(serializer.data)


@api_view(["GET"])
def retrieve_all_synced_farm_data(request):
    data = EUDRFarmBackupModel.objects.all().order_by("-updated_at")

    serializer = EUDRFarmBackupModelSerializer(data, many=True)

    return Response(serializer.data)


@api_view(["GET"])
def retrieve_all_synced_farm_data_by_cs(request, pk):
    data = EUDRFarmBackupModel.objects.filter(
        site_id=pk
    ).order_by("-updated_at")

    serializer = EUDRFarmBackupModelSerializer(data, many=True)

    return Response(serializer.data)


@api_view(["GET"])
def retrieve_collection_sites(request):
    data = EUDRCollectionSiteModel.objects.all().order_by("-updated_at")

    serializer = EUDRCollectionSiteModelSerializer(data, many=True)

    return Response(serializer.data)


@api_view(["GET"])
def retrieve_map_data(request):
    files = EUDRUploadedFilesModel.objects.filter(
        uploaded_by=request.user.username if request.user.is_authenticated else "admin"
    )
    filesSerializer = EUDRUploadedFilesModelSerializer(files, many=True)

    data = EUDRFarmModel.objects.filter(
        file_id__in=[file["id"] for file in filesSerializer.data]
    ).order_by("-updated_at") if not request.user.is_staff else EUDRFarmModel.objects.all().order_by("-updated_at")

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
    data = None
    if request.user.is_authenticated:
        # Filter by the authenticated user's username
        data = EUDRUploadedFilesModel.objects.filter(
            uploaded_by=request.user.username).order_by("-updated_at") if not request.user.is_staff else EUDRUploadedFilesModel.objects.all().order_by("-updated_at")
    else:
        # Retrieve all records if no authenticated user
        data = EUDRUploadedFilesModel.objects.all().order_by("-updated_at")
    serializer = EUDRUploadedFilesModelSerializer(data, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def retrieve_s3_files(request):
    # Retrieve all files from all directories in the S3 bucket
    s3 = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                      aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
    response = s3.list_objects_v2(Bucket=settings.AWS_STORAGE_BUCKET_NAME)
    # get file urls and date uploaded
    files = []
    count = 0
    for content in response.get('Contents', []):
        file = {
            'id': count,
            'file_name': content.get('Key').split("/")[1].split("_", 1)[1],
            'last_modified': content.get('LastModified'),
            'size': content.get('Size') / 1024,
            'url': f"{settings.AWS_S3_BASE_URL}{content.get('Key')}",
            'uploaded_by': content.get('Key').split("/")[1].split("_")[0],
            'category': content.get('Key').split("/")[0],
        }
        files.append(file)
        count += 1

    return Response(files)


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


@api_view(["POST"])
def generate_map_link(request):
    fileId = request.data.get("file-id")
    try:
        shared_map_access = EUDRSharedMapAccessCodeModel.objects.get(
            file_id=fileId)
        if shared_map_access.valid_until >= timezone.now():
            access_code = shared_map_access.access_code
        else:
            raise EUDRSharedMapAccessCodeModel.DoesNotExist
    except EUDRSharedMapAccessCodeModel.DoesNotExist:
        access_code = generate_access_code()
        valid_until = timezone.now() + timedelta(days=90)
        shared_map_access = EUDRSharedMapAccessCodeModel.objects.create(
            file_id=fileId,
            access_code=access_code,
            valid_until=valid_until
        )

    map_link = f"""{request.scheme}://{request.get_host()
                                       }/map/share/?file-id={fileId}&access-code={access_code}"""

    return Response({"access_code": access_code, "map_link": map_link}, status=status.HTTP_200_OK)


def generate_access_code():
    return str(uuid.uuid4())


class CustomPasswordResetView(PasswordResetView):
    email_template_name = 'password_reset_email.html'
    subject_template_name = 'password_reset_subject.txt'
    success_url = 'password_reset_done'
