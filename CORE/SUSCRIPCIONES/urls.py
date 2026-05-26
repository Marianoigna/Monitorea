from django.urls import path
from . import views

app_name = 'suscripciones'

urlpatterns = [
    path('suscribirse/', views.crear_suscripcion, name='suscribirse'),
    path('webhook/',     views.webhook,           name='webhook'),
]
