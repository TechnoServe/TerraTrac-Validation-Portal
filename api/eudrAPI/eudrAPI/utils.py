import ast
import random
import string
import requests
import os
from dotenv import load_dotenv

load_dotenv()


def get_auth_token():
    url = f"{os.getenv('API_BASE_URL')}/auth/token"
    data = {
        "username": os.getenv("GFW_USERNAME"),
        "password": os.getenv("GFW_PASSWORD"),
    }
    response = requests.post(url, data=data)
    json_response = response.json()
    if json_response.get("status") == "success":
        return json_response.get("data").get("access_token")
    else:
        return None


def get_api_key(token):
    random_alias = (
        random.choice(string.ascii_letters).upper()
        + random.choice(string.ascii_letters).upper()
    )
    url = f"{os.getenv('API_BASE_URL')}/auth/apikey"
    data = {
        "alias": f"api-key-for-TNS-{random_alias}",
        "email": os.getenv("EMAIL"),
        "organization": os.getenv("ORGANIZATION"),
        "domains": ast.literal_eval(os.getenv("DOMAINS")),
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(url, headers=headers, json=data)
    json_response = response.json()
    return (
        json_response.get("data") if json_response.get("status") == "success" else None
    )
