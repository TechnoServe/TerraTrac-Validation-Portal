from django.urls import path
from .views import index
from my_eudr_app import views

urlpatterns = [
    path("", index),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
]
