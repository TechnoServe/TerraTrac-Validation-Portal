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
from asgiref.sync import async_to_sync
from django.contrib.auth.models import User
import boto3
from shapely import Polygon

from eudr_backend import settings
from eudr_backend.async_tasks import async_create_farm_data
from eudr_backend.models import EUDRCollectionSiteModel, EUDRFarmBackupModel, EUDRSharedMapAccessCodeModel, EUDRFarmModel, EUDRUploadedFilesModel, EUDRUserModel
from eudr_backend.tasks import update_geoid
from datetime import timedelta

from eudr_backend.utils import extract_data_from_file, flatten_multipolygon_coordinates, generate_access_code, handle_failed_file_entry, store_failed_file_in_s3, transform_csv_to_json, transform_db_data_to_geojson
from eudr_backend.validators import validate_csv, validate_geojson
from .serializers import (
    EUDRCollectionSiteModelSerializer,
    EUDRFarmBackupModelSerializer,
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


@api_view(["POST"])
def create_farm_data(request):
    data_format = request.data.get('format', "geojson") if isinstance(
        request.data, dict) else "geojson"
    raw_data = json.loads(request.data) if isinstance(
        request.data, str) else request.data
    file = request.FILES.get('file')

    # Validate that either file or raw_data is provided
    if not file and not raw_data:
        return Response({'error': 'Either a file or data is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Determine the data source (file or raw_data)
    if file:
        file_name = file.name.split('.')[0]
        # Custom function to read data from file if needed
        raw_data = extract_data_from_file(file, data_format)
    else:
        file_name = "uploaded_data"

    # Validate the format
    if not data_format or not raw_data:
        return Response({'error': 'Format and data are required'}, status=status.HTTP_400_BAD_REQUEST)
    elif data_format == 'geojson':
        errors = validate_geojson(raw_data)
    elif data_format == 'csv':
        errors = validate_csv(raw_data)
    else:
        return Response({'error': 'Unsupported format'}, status=status.HTTP_400_BAD_REQUEST)

    if errors:
        # Custom function to handle S3 upload
        store_failed_file_in_s3(file, request.user, file_name)
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

    if data_format == 'csv':
        raw_data = transform_csv_to_json(raw_data)

    serializer = EUDRFarmModelSerializer(data=request.data)

    # Combine file_name and format for database entry
    file_data = {
        "file_name": f"{file_name}.{data_format}",
        "uploaded_by": request.user.username if request.user.is_authenticated else "admin",
    }
    file_serializer = EUDRUploadedFilesModelSerializer(data=file_data)

    if file_serializer.is_valid():
        if not EUDRUploadedFilesModel.objects.filter(
            file_name=file_data["file_name"],
            uploaded_by=request.user.username if request.user.is_authenticated else "admin"
        ).exists():
            file_serializer.save()
        file_id = EUDRUploadedFilesModel.objects.get(
            file_name=file_data["file_name"],
            uploaded_by=request.user.username if request.user.is_authenticated else "admin"
        ).id

        errors, created_data = async_to_sync(async_create_farm_data)(
            raw_data, serializer, file_id)
        if errors:
            # Custom function to handle failed file entries
            handle_failed_file_entry(file_serializer, file, request.user)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        # Custom function to handle failed file entries
        handle_failed_file_entry(file_serializer, file, request.user)
        return Response({'error': 'File serialization failed'}, status=status.HTTP_400_BAD_REQUEST)

    # Proceed with other operations...
    return Response({'message': 'File/data processed successfully', 'file_id': file_id}, status=status.HTTP_201_CREATED)


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
