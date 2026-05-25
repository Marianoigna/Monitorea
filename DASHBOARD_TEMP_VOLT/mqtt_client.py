"""
mqtt_client.py — Suscriptor MQTT integrado en Django
=====================================================
Corre en un hilo de fondo dentro del mismo proceso Daphne/ASGI.
Recibe mensajes MQTT desde sensores de temperatura (ESP32 u otros) y los
persiste directamente con el ORM de Django, luego notifica a los clientes
WebSocket vía Channels (sin llamadas HTTP).

Variables de entorno opcionales:
  MQTT_BROKER        broker MQTT (default: broker.emqx.io)
  MQTT_PORT          puerto WebSocket SSL (default: 8084)
  MQTT_TOPIC_TEMP    topic de temperatura (default: temperatura_prueba)
  MQTT_TOPIC_VOLT    topic de voltaje     (default: voltaje_prueba)
  MQTT_USER          usuario (default: vacío)
  MQTT_PASSWORD      contraseña (default: vacío)
"""

import json
import os
import threading

import paho.mqtt.client as mqtt
from asgiref.sync import async_to_sync

# ── Configuración ──────────────────────────────────────────────────────────────
MQTT_BROKER     = os.environ.get('MQTT_BROKER',     'broker.emqx.io')
MQTT_PORT       = int(os.environ.get('MQTT_PORT',   '8084'))
MQTT_TOPIC_TEMP = os.environ.get('MQTT_TOPIC_TEMP', 'temperatura_prueba')
MQTT_TOPIC_VOLT = os.environ.get('MQTT_TOPIC_VOLT', 'voltaje_prueba')
MQTT_USER       = os.environ.get('MQTT_USER',       '')
MQTT_PASSWORD   = os.environ.get('MQTT_PASSWORD',   '')
# ──────────────────────────────────────────────────────────────────────────────

_thread: threading.Thread | None = None


def _on_connect(client, userdata, flags, reason_code, properties):
    print(f'[MQTT] Conectado a {MQTT_BROKER}:{MQTT_PORT}')
    client.subscribe(MQTT_TOPIC_TEMP)
    client.subscribe(MQTT_TOPIC_VOLT)
    print(f'[MQTT] Suscrito a: {MQTT_TOPIC_TEMP}, {MQTT_TOPIC_VOLT}')


def _on_message(client, userdata, msg):
    # Imports diferidos para evitar ciclos en el arranque de Django
    from channels.layers import get_channel_layer
    from DASHBOARD_TEMP_VOLT.models import Temperatura, Voltaje

    topic   = msg.topic
    payload = msg.payload.decode('utf-8').strip()
    is_temp = (topic == MQTT_TOPIC_TEMP)

    try:
        try:
            data      = json.loads(payload)
            valor     = float(data.get('valor', data))
            sensor_id = data.get('sensor_id', 'sensor_01' if is_temp else 'voltaje_01')
        except (json.JSONDecodeError, TypeError):
            valor     = float(payload)
            sensor_id = 'sensor_01' if is_temp else 'voltaje_01'

        channel_layer = get_channel_layer()

        if is_temp:
            registro = Temperatura.objects.create(valor=valor, sensor_id=sensor_id)
            async_to_sync(channel_layer.group_send)('temperatura', {
                'type':      'send_temperatura',
                'sensor_id': registro.sensor_id,
                'valor':     registro.valor,
                'timestamp': registro.timestamp.isoformat(),
            })
            print(f'[MQTT] ✔ temperatura: {sensor_id} → {valor}°C')
        else:
            registro = Voltaje.objects.create(valor=valor, sensor_id=sensor_id)
            async_to_sync(channel_layer.group_send)('voltaje', {
                'type':      'send_voltaje',
                'sensor_id': registro.sensor_id,
                'valor':     registro.valor,
                'timestamp': registro.timestamp.isoformat(),
            })
            print(f'[MQTT] ✔ voltaje:     {sensor_id} → {valor}V')

    except Exception as e:
        print(f'[MQTT] ✘ Error procesando "{topic}" payload={payload!r}: {e}')


def _run():
    import time
    retry_delay = 5
    while True:
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport='websockets')
            client.tls_set()  # SSL para WSS (puerto 8084)
            if MQTT_USER:
                client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
            client.on_connect = _on_connect
            client.on_message = _on_message

            print(f'[MQTT] Conectando a {MQTT_BROKER}:{MQTT_PORT}...')
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            client.loop_forever()
            retry_delay = 5
        except Exception as e:
            print(f'[MQTT] Error de conexión: {type(e).__name__}: {e}')
            print(f'[MQTT] Reintentando en {retry_delay}s...')
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)


def start():
    """Arranca el hilo MQTT si no está ya corriendo."""
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_run, name='mqtt-subscriber', daemon=True)
    _thread.start()
    print('[MQTT] Hilo de suscripción iniciado.')
