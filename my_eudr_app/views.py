from django.shortcuts import render


def index(request):
    active_page = "index"

    return render(request, "index.html", {"active_page": active_page})


def validator(request):
    active_page = "validator"

    return render(request, "validator.html", {"active_page": active_page})


def map(request):
    active_page = "map"

    return render(request, "map.html", {"active_page": active_page})


def users(request):
    active_page = "users"

    return render(request, "users.html", {"active_page": active_page})
