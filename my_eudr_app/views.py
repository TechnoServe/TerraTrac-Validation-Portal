import os
from django.shortcuts import render
import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from dotenv import load_dotenv


def index(request):
    return render(request, "index.html")


def validator(request):
    return render(request, "validator.html")


def map(request):
    return render(request, "map.html")


def users(request):
    return render(request, "users.html")


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
