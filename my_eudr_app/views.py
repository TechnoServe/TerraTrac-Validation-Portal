from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages


@login_required
def index(request):
    active_page = "index"

    return render(request, "index.html", {"active_page": active_page, 'user': request.user})


@login_required
def validator(request):
    active_page = "validator"

    return render(request, "validator.html", {"active_page": active_page, 'user': request.user})


@login_required
def validated_files(request):
    active_page = "validated_files"

    return render(request, "validated_files.html", {"active_page": active_page, 'user': request.user})


@login_required
def map(request):
    active_page = "map"

    return render(request, "map.html", {"active_page": active_page, 'user': request.user})


def shared_map(request):
    active_page = "shared_map"

    return render(request, "shared_map.html", {"active_page": active_page, 'user': request.user})


@login_required
@staff_member_required(login_url='/login/')
def users(request):
    active_page = "users"

    return render(request, "users.html", {"active_page": active_page, 'user': request.user})

@login_required
@staff_member_required(login_url='/login/')
def backups(request):
    active_page = "backups"

    return render(request, "backups.html", {"active_page": active_page, 'user': request.user})

@login_required
@staff_member_required(login_url='/login/')
def backup_details(request):
    active_page = "backup_details"

    return render(request, "backup_details.html", {"active_page": active_page, 'user': request.user})

@login_required
@staff_member_required(login_url='/login/')
def all_uploaded_files(request):
    active_page = "uploads"

    return render(request, "uploads.html", {"active_page": active_page, 'user': request.user})


@login_required
def profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')
    return render(request, 'profile.html')
