from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Temperatura, Voltaje
from .serializers import TemperaturaSerializer, VoltajeSerializer


# ── API REST ──────────────────────────────────────────────────────────────────

class TemperaturaAPIView(APIView):
    """
    GET  /api/temperatura/       → últimas 50 lecturas
    POST /api/temperatura/       → guarda nueva lectura y notifica WebSocket
    """

    def get(self, request):
        registros = Temperatura.objects.all()[:50]
        serializer = TemperaturaSerializer(registros, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = TemperaturaSerializer(data=request.data)
        if serializer.is_valid():
            registro = serializer.save()

            # Notificar a todos los clientes WebSocket conectados
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'temperatura',
                {
                    'type': 'send_temperatura',
                    'sensor_id': registro.sensor_id,
                    'valor': registro.valor,
                    'timestamp': registro.timestamp.isoformat(),
                }
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── Vista HTML ────────────────────────────────────────────────────────────────

class VoltajeAPIView(APIView):
    """
    GET  /api/voltaje/  → últimas 50 lecturas
    POST /api/voltaje/  → guarda nueva lectura y notifica WebSocket
    """

    def get(self, request):
        registros = Voltaje.objects.all()[:50]
        serializer = VoltajeSerializer(registros, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = VoltajeSerializer(data=request.data)
        if serializer.is_valid():
            registro = serializer.save()
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                'voltaje',
                {
                    'type': 'send_voltaje',
                    'sensor_id': registro.sensor_id,
                    'valor': registro.valor,
                    'timestamp': registro.timestamp.isoformat(),
                }
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def dashboard(request):
    """Página principal con temperatura y voltaje en tiempo real."""
    ultimos_temp = Temperatura.objects.all()[:5]
    ultima_temp = ultimos_temp[0] if ultimos_temp else None
    ultimo_volt = Voltaje.objects.first()
    return render(request, 'DASHBOARD_TEMP_VOLT/dashboard.html', {
        'ultima': ultima_temp,
        'ultimos': list(reversed(list(ultimos_temp))),
        'ultimo_volt': ultimo_volt,
    })
