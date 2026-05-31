import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Establecimiento, Dispositivo, Temperatura, Voltaje

logger = logging.getLogger(__name__)


# ── Vistas HTML ───────────────────────────────────────────────────────────────

def landing(request):
    """Página de bienvenida pública."""
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    return render(request, 'DASHBOARD/landing.html')


@login_required
def dashboard(request):
    """Dashboard principal — establecimientos, dispositivos y sensores del usuario."""
    establecimientos = (
        request.user.establecimientos
        .prefetch_related('dispositivos__sensores')
        .all()
    )
    return render(request, 'DASHBOARD/dashboard.html', {
        'establecimientos': establecimientos,
    })


# ── AJAX — Crear Establecimiento ──────────────────────────────────────────────

@login_required
@require_POST
def crear_establecimiento(request):
    try:
        data = json.loads(request.body)
        nombre = data.get('nombre', '').strip()
        if not nombre:
            return JsonResponse({'error': 'El nombre es requerido.'}, status=400)
        estab = Establecimiento.objects.create(usuario=request.user, nombre=nombre)
        return JsonResponse({
            'id': estab.id,
            'nombre': estab.nombre,
            'empresa': request.user.empresa,
        }, status=201)
    except Exception as e:
        logger.error('crear_establecimiento: %s', e)
        return JsonResponse({'error': 'Error interno.'}, status=500)


# ── AJAX — Crear Dispositivo ──────────────────────────────────────────────────

@login_required
@require_POST
def crear_dispositivo(request):
    try:
        data = json.loads(request.body)
        nombre = data.get('nombre', '').strip()
        mac_address = data.get('mac_address', '').strip().upper()
        establecimiento_id = data.get('establecimiento_id')

        if not nombre or not mac_address or not establecimiento_id:
            return JsonResponse({'error': 'Todos los campos son requeridos.'}, status=400)

        try:
            estab = Establecimiento.objects.get(id=establecimiento_id, usuario=request.user)
        except Establecimiento.DoesNotExist:
            return JsonResponse({'error': 'Establecimiento no encontrado.'}, status=404)

        if Dispositivo.objects.filter(mac_address=mac_address).exists():
            return JsonResponse({'error': 'La dirección MAC ya está registrada.'}, status=400)

        dispositivo = Dispositivo.objects.create(
            establecimiento=estab,
            nombre=nombre,
            mac_address=mac_address,
        )
        return JsonResponse({
            'id': dispositivo.id,
            'nombre': dispositivo.nombre,
            'mac_address': dispositivo.mac_address,
            'establecimiento_id': estab.id,
        }, status=201)
    except Exception as e:
        logger.error('crear_dispositivo: %s', e)
        return JsonResponse({'error': 'Error interno.'}, status=500)


# ── API Telemetría ─────────────────────────────────────────────────────────────

class TelemetriaAPIView(APIView):
    """
    POST /api/telemetria/<mac>/
    Payload: {"t": [25.4, 28.1], "v": [220.5]}
    Registra lecturas y notifica por WebSocket al grupo del dispositivo.
    """

    def post(self, request, mac):
        mac = mac.upper()
        try:
            dispositivo = Dispositivo.objects.get(mac_address=mac)
        except Dispositivo.DoesNotExist:
            return Response({'error': 'Dispositivo no registrado.'}, status=status.HTTP_404_NOT_FOUND)

        t_values = request.data.get('t', [])
        v_values = request.data.get('v', [])

        for canal, valor in enumerate(t_values):
            Temperatura.objects.create(dispositivo=dispositivo, canal=canal, valor=valor)
        for canal, valor in enumerate(v_values):
            Voltaje.objects.create(dispositivo=dispositivo, canal=canal, valor=valor)

        group = f'telemetria_{mac.replace(":", "_")}'
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            group,
            {
                'type': 'send_telemetria',
                'mac': mac,
                't': list(enumerate(t_values)),
                'v': list(enumerate(v_values)),
            }
        )
        return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)
