"""
URL configuration for eudr_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path

from eudr_backend.views import (
    create_farm_data,
    download_template,
    get_radd_data,
    retrieve_farm_data,
)
from my_eudr_app import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path("validator/", views.validator, name="validator"),
    path("map/", views.map, name="map"),
    path("users/", views.users, name="users"),
    path("api/farm/add/", create_farm_data, name="create_farm_data"),
    path("api/farm/list/", retrieve_farm_data, name="retrieve_farm_data"),
    path(
        "api/get-radd-data/",
        get_radd_data,
        name="get_radd_data",
    ),
    path("api/download-template/", download_template, name="download_template"),
]
