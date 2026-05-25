from django.shortcuts import render

from SUSCRIPCIONES.decorators import requiere_premium


@requiere_premium
def index(request):
    """Vista principal de reportes históricos — requiere suscripción premium."""
    return render(request, 'REPORTES/index.html')
