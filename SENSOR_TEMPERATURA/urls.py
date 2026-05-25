from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/temperatura/', views.TemperaturaAPIView.as_view(), name='api_temperatura'),
]
