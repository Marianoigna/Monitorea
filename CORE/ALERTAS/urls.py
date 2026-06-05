from django.urls import path
from . import views

app_name = 'alertas'

urlpatterns = [
    path('',          views.alertas_index,  name='alertas_index'),
    path('guardar/',  views.guardar_alerta, name='guardar_alerta'),
]
