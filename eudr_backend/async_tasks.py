import json
import httpx
from asgiref.sync import sync_to_async
from django.db.models import Q
from eudr_backend.models import EUDRFarmModel, EUDRUploadedFilesModel, WhispAPISetting
from eudr_backend.serializers import EUDRFarmModelSerializer
from eudr_backend.utils import flatten_geojson, format_geojson_data, transform_db_data_to_geojson


# Define an async function
async def async_create_farm_data(data, serializer, file_id, isSyncing=False, hasCreatedFiles=[]):
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
