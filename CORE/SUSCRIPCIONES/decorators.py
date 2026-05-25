from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def requiere_premium(view_func):
    """
    Decorator para vistas que requieren suscripción premium activa.

    Flujo:
      1. Si el usuario no está autenticado → redirige a login.
      2. Si no tiene suscripción o está vencida → redirige al dashboard
         con un mensaje informativo.
      3. Si tiene suscripción activa → permite el acceso.

    Uso:
        from SUSCRIPCIONES.decorators import requiere_premium

        @requiere_premium
        def mi_vista(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        try:
            suscripcion = request.user.suscripcion
            if suscripcion.esta_activa():
                return view_func(request, *args, **kwargs)
        except Exception:
            pass

        messages.warning(
            request,
            'Esta sección requiere una suscripción premium activa. '
            'Activá tu plan para acceder a reportes y alertas.',
        )
        return redirect('dashboard:dashboard')

    return wrapper
