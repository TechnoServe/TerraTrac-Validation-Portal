from django.shortcuts import redirect, render
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings


def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.email = request.POST.get('username')
            user.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'auth/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('index')
    else:
        form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Important to keep the user logged in
            update_session_auth_hash(request, user)
            messages.success(
                request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        return redirect('login')


def password_reset_request(request):
    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data['email']
            associated_users = User.objects.filter(email=data)
            if associated_users.exists():
                for user in associated_users:
                    subject = "TerraTrav Validation Portal - Password Reset Requested"
                    email_template_name = "auth/password_reset_email.html"
                    c = {
                        "email": user.email,
                        "domain": request.get_host(),
                        "site_name": "TerraTrac Validation Portal",
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        "token": default_token_generator.make_token(user),
                        "protocol": 'https' if request.is_secure() else 'http',
                    }
                    email = render_to_string(email_template_name, c)
                    send_mail(subject, message=email, html_message=email,
                              from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[user.email])

                messages.success(
                    request, 'A link to reset your password has been sent to your email address.')
                return redirect(reverse('password_reset'))
            else:
                messages.error(
                    request, 'No user found with this email address.')
                return redirect(reverse('password_reset'))

    password_reset_form = PasswordResetForm()
    return render(request, "auth/password_reset.html", {"form": password_reset_form})


def password_reset_confirm(request, uidb64=None, token=None):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(
                    request, 'Your password has been successfully reset. You can now log in with your new password.')
                return redirect('login')
        else:
            form = SetPasswordForm(user)
    else:
        messages.error(
            request, 'The password reset link is invalid or has expired.')
        return redirect('password_reset')

    return render(request, 'auth/password_reset_confirm.html', {'form': form})
