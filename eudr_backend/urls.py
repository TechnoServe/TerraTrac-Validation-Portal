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
    create_user,
    delete_user,
    download_template,
    retrieve_farm_data,
    retrieve_farm_data_from_file_id,
    retrieve_farm_detail,
    retrieve_files,
    retrieve_user,
    retrieve_users,
    update_user,
)
from my_eudr_app import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path("validator/", views.validator, name="validator"),
    path("validated_files/", views.validated_files, name="validated_files"),
    path("map/", views.map, name="map"),
    path("users/", views.users, name="users"),
    path("api/users/", retrieve_users, name="user_list"),
    path("api/users/<int:pk>/", retrieve_user, name="user_detail"),
    path("api/users/add/", create_user, name="user_create"),
    path("api/users/update/<int:pk>/", update_user, name="user_update"),
    path("api/users/delete/<int:pk>/", delete_user, name="user_delete"),
    path("api/farm/add/", create_farm_data, name="create_farm_data"),
    path("api/farm/list/", retrieve_farm_data, name="retrieve_farm_data"),
    path("api/farm/list/<int:pk>/", retrieve_farm_detail, name="retrieve_farm_detail"),
    path("api/files/list/", retrieve_files, name="retrieve_files"),
    path(
        "api/farm/list/file/<int:pk>/",
        retrieve_farm_data_from_file_id,
        name="retrieve_farm_data_from_file_id",
    ),
    path("api/download-template/", download_template, name="download_template"),
]
