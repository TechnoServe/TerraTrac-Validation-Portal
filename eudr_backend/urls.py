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
from django.urls import include, path

from eudr_backend.views import (
    create_farm_data,
    create_user,
    delete_user,
    download_template,
    generate_map_link,
    restore_farm_data,
    retrieve_all_synced_farm_data,
    retrieve_all_synced_farm_data_by_cs,
    retrieve_collection_sites,
    retrieve_farm_data,
    retrieve_farm_data_from_file_id,
    retrieve_farm_detail,
    retrieve_file,
    retrieve_files,
    retrieve_map_data,
    retrieve_overlapping_farm_data,
    retrieve_s3_files,
    retrieve_user,
    retrieve_user_farm_data,
    retrieve_users,
    revalidate_farm_data,
    sync_farm_data,
    update_farm_data,
    update_user,
)
from my_eudr_app import auth_views, map_views, views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path("auth/", include("my_eudr_app.urls")),
    path("validator/", views.validator, name="validator"),
    path("validated_files/", views.validated_files, name="validated_files"),
    path("map/", views.map, name="map"),
    path("map/share/", views.shared_map, name="shared_map"),
    path("map_data", map_views.map_view, name="map_view"),
    path("users/", views.users, name="users"),
    path("backups/", views.backups, name="backups"),
    path("backup_details/", views.backup_details, name="backup_details"),
    path("uploads/", views.all_uploaded_files, name="uploads"),
    path("profile/", views.profile, name="profile"),
    path('profile/change-password/',
         auth_views.change_password, name='change_password'),
    path("logout/", auth_views.logout_view, name="logout"),
    path("api/users/", retrieve_users, name="user_list"),
    path("api/users/<int:pk>/", retrieve_user, name="user_detail"),
    path("api/users/add/", create_user, name="user_create"),
    path("api/users/update/<int:pk>/", update_user, name="user_update"),
    path("api/users/delete/<int:pk>/", delete_user, name="user_delete"),
    path("api/farm/add/", create_farm_data, name="create_farm_data"),
    path("api/farm/update/<int:pk>/", update_farm_data, name="update_farm_data"),
    path("api/farm/sync/", sync_farm_data, name="sync_farm_data"),
    path("api/farm/restore/", restore_farm_data, name="restore_farm_data"),
    path("api/farm/revalidate/<int:pk>/", revalidate_farm_data,
         name="revalidate_farm_data"),
    path("api/farm/list/", retrieve_farm_data, name="retrieve_farm_data"),
    path("api/farm/overlapping/<int:pk>/", retrieve_overlapping_farm_data,
         name="retrieve_overlapping_farm_data"),
    path("api/farm/list/user/<int:pk>/",
         retrieve_user_farm_data, name="retrieve_user_farm_data"),
    path("api/farm/sync/list/all/", retrieve_all_synced_farm_data,
         name="retrieve_all_synced_farm_data"),
    path("api/farm/sync/list/<int:pk>/", retrieve_all_synced_farm_data_by_cs,
         name="retrieve_all_synced_farm_data_by_cs"),
    path("api/farm/map/list/", retrieve_map_data, name="retrieve_map_data"),
    path("api/farm/list/<int:pk>/", retrieve_farm_detail,
         name="retrieve_farm_detail"),
    path("api/collection_sites/list/", retrieve_collection_sites,
         name="retrieve_collection_sites"),
    path("api/files/list/", retrieve_files, name="retrieve_files"),
    path("api/files/list/all/", retrieve_s3_files, name="retrieve_all_files"),
    path("api/files/list/<int:pk>/", retrieve_file, name="retrieve_file"),
    path(
        "api/farm/list/file/<int:pk>/",
        retrieve_farm_data_from_file_id,
        name="retrieve_farm_data_from_file_id",
    ),
    path("api/download-template/", download_template, name="download_template"),
    path("api/map-share/", generate_map_link, name="map_share"),
]
