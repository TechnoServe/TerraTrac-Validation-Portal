from django.urls import path
from .views import index
from my_eudr_app import auth_views, views

urlpatterns = [
    path("", index),
    path("login/", auth_views.login_view, name="login"),
    path("signup/", auth_views.signup_view, name="signup"),
    path("password_reset/", auth_views.password_reset_request, name="password_reset"),
    path("reset/<uidb64>/<token>/", auth_views.password_reset_confirm,
         name="password_reset_confirm"),
]
