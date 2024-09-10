from django.urls import path
from .views import index
from my_eudr_app import views

urlpatterns = [
    path("", index),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("password_reset/", views.password_reset_request, name="password_reset"),
    path("reset/<uidb64>/<token>/", views.password_reset_confirm,
         name="password_reset_confirm"),
]
