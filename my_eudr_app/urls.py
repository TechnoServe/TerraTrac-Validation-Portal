from django.urls import path
from .views import get_radd_data

urlpatterns = [
    path(
        "get-radd-data/",
        get_radd_data,
        name="get_radd_data",
    ),
]
