from django.shortcuts import render

from SUSCRIPCIONES.decorators import requiere_premium


@requiere_premium
def index(request):
    """Vista principal de configuración de alertas — requiere suscripción premium."""
    return render(request, 'ALERTAS/index.html')
