from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('api/telemetria/<str:mac>/', views.TelemetriaAPIView.as_view(), name='api_telemetria'),
    path('api/telemetria/<str:mac>/historial/', views.historial_telemetria, name='historial_telemetria'),
    path('api/telemetria/<str:mac>/sensores-activos/', views.sensores_activos, name='sensores_activos'),
    path('api/establecimientos/crear/', views.crear_establecimiento, name='crear_establecimiento'),
    path('api/dispositivos/crear/', views.crear_dispositivo, name='crear_dispositivo'),
]
