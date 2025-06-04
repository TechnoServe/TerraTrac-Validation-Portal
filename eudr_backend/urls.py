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
from django.shortcuts import render
from django.urls import include, path, re_path

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
    filter_backup,
    filter_total_files,
    retrieve_files_with_filter,
    retrieve_users_filter,
    filter_dashboard_metrics,
    filter_total_plots
)
from my_eudr_app import auth_views, map_views, views
from rest_framework import permissions
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

schema_view = get_schema_view(
    openapi.Info(
        title="Terratrac API Documentation",
        default_version="v1",
        description="TerraTrac Validation Portal allows users to upload the list of plot geolocation data (point when the plot is less than 4 hectares, and polygon when the plot is bigger), then runs these data though a deforestation database using WHisp API for risk assessment,then generates reports for exporters.",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="support@tnslabs.atlassian.net"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("my_eudr_app.urls")),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger',
         cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc',
         cache_timeout=0), name='schema-redoc'),
    path("", views.index, name="index"),
#     path("auth/", include("my_eudr_app.urls")),
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
    path("api/farm/revalidate/", revalidate_farm_data,
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


    path("user-guide/", lambda request: render(request, "user_guide.html"), name="user_guide"),
    path('api/filtered_plots/list/all/',filter_total_plots , name='total_plots'),
    path('api/filtered_files/list/', retrieve_files_with_filter, name='total_files'),
    path('api/filtered_users/',retrieve_users_filter, name='users_filter'),
    path('api/collection_sites/filter/', filter_backup, name='filter_backups'),
    path('uploads/api/filtered_files/list/all/', filter_total_files, name='total_files'),
    path('api/dashboard/metrics/', filter_dashboard_metrics, name='dashboard_metrics'),


]
