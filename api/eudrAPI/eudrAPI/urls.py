"""
URL configuration for tnsAPI project.

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

from django.urls import path

from .views import get_radd_data, get_tree_cover_loss_data


urlpatterns = [
    path(
        "get-tree-cover-loss-data/",
        get_tree_cover_loss_data,
        name="get_tree_cover_loss_data",
    ),
    path(
        "get-radd-data/",
        get_radd_data,
        name="get_radd_data",
    ),
]
