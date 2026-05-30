import json

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegisterForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(request.GET.get('next', '/'))
    else:
        form = LoginForm(request)

    return render(request, 'ACCOUNTS/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:login')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'¡Bienvenido, {user.username}! Tu cuenta fue creada.')
            return redirect('dashboard:dashboard')
    else:
        form = RegisterForm()

    return render(request, 'ACCOUNTS/register.html', {'form': form})


@login_required
@require_POST
def set_theme(request):
    """Guarda la preferencia de tema del usuario autenticado."""
    try:
        data = json.loads(request.body)
        theme = data.get('theme')
        if theme in ('light', 'dark', 'auto'):
            request.user.theme = theme
            request.user.save(update_fields=['theme'])
            return JsonResponse({'status': 'ok', 'theme': theme})
    except (json.JSONDecodeError, KeyError):
        pass
    return JsonResponse({'status': 'error'}, status=400)
