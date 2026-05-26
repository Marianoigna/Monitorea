from django.urls import path
from . import views

app_name = 'suscripciones'

urlpatterns = [
    # Flujo de suscripción recurrente (preapproval — se activa cuando el plan esté creado en MP)
    path('suscribirse/',    views.crear_suscripcion, name='suscribirse'),
    path('webhook/',        views.webhook,           name='webhook'),

    # Flujo de prueba obligatorio para validar la integración en el panel de MP
    path('checkout-prueba/',  views.checkout_pro_prueba, name='checkout_prueba'),
    path('pago-exitoso/',     views.pago_exitoso,        name='pago_exitoso'),
    path('pago-fallido/',     views.pago_fallido,        name='pago_fallido'),
    path('pago-pendiente/',   views.pago_pendiente,      name='pago_pendiente'),
]
