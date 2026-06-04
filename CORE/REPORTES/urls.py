from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.index, name='index'),
    path('datos/', views.obtener_datos_reporte, name='obtener_datos_reporte'),
    path('exportar/', views.exportar_csv, name='exportar_csv'),
]
