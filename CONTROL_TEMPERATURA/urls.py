"""
URL configuration for CONTROL_TEMPERATURA project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('DASHBOARD_TEMP_VOLT.urls')),
]
