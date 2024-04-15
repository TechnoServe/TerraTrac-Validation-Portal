import os
from dotenv import load_dotenv
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
