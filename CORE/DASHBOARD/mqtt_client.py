"""
mqtt_client.py — Suscriptor MQTT integrado en Django
=====================================================
Corre en un hilo de fondo dentro del mismo proceso Daphne/ASGI.
Recibe mensajes MQTT, los persiste con el ORM de Django y notifica
a los clientes WebSocket vía Channels.

Tópico esperado:
  dispositivos/<MAC_ADDRESS>/telemetria

Payload JSON:
  {"t": [25.4, 28.1], "v": [220.5]}

Variables de entorno opcionales:
  MQTT_BROKER    broker MQTT (default: broker.emqx.io)
  MQTT_PORT      puerto WebSocket SSL (default: 8084)
  MQTT_USER      usuario (default: vacío)
  MQTT_PASSWORD  contraseña (default: vacío)
"""

import json
import os
import threading
from datetime import datetime, timezone as dt_timezone

import paho.mqtt.client as mqtt
from asgiref.sync import async_to_sync

# ── Configuración ──────────────────────────────────────────────────────────────
MQTT_BROKER   = os.environ.get('MQTT_BROKER',   'broker.emqx.io')
MQTT_PORT     = int(os.environ.get('MQTT_PORT', '8084'))
MQTT_TOPIC    = 'dispositivos/+/telemetria'
MQTT_USER     = os.environ.get('MQTT_USER',     '')
MQTT_PASSWORD = os.environ.get('MQTT_PASSWORD', '')
# ──────────────────────────────────────────────────────────────────────────────

_thread: threading.Thread | None = None


def _mac_from_topic(topic: str) -> str:
    """Extrae la MAC del tópico 'dispositivos/<MAC>/telemetria'."""
    return topic.split('/')[1].upper()


def _on_connect(client, userdata, flags, reason_code, properties):
    print(f'[MQTT] Conectado a {MQTT_BROKER}:{MQTT_PORT}')
    client.subscribe(MQTT_TOPIC)
    print(f'[MQTT] Suscrito a: {MQTT_TOPIC}')


def _on_message(client, userdata, msg):
    # Imports diferidos para evitar ciclos en el arranque de Django
    from channels.layers import get_channel_layer
    from DASHBOARD.models import Dispositivo, Telemetria

    topic   = msg.topic
    payload = msg.payload.decode('utf-8').strip()

    try:
        mac  = _mac_from_topic(topic)
        data = json.loads(payload)
    except (IndexError, json.JSONDecodeError) as e:
        print(f'[MQTT] ✘ Tópico o payload inválido: {topic} — {e}')
        return

    try:
        dispositivo = Dispositivo.objects.select_related(
            'establecimiento__usuario'
        ).get(mac_address=mac)
    except Dispositivo.DoesNotExist:
        print(f'[MQTT] ✘ Dispositivo no registrado: {mac}')
        return

    t_values = data.get('t', [])
    v_values = data.get('v', [])
    timestamp = datetime.now(dt_timezone.utc).isoformat()

    lecturas = []
    for canal, valor in enumerate(t_values):
        Telemetria.objects.create(
            dispositivo=dispositivo, tipo_sensor='temperatura', canal=canal, valor=valor
        )
        lecturas.append({'tipo': 'temperatura', 'canal': canal, 'valor': valor})

    for canal, valor in enumerate(v_values):
        Telemetria.objects.create(
            dispositivo=dispositivo, tipo_sensor='tension', canal=canal, valor=valor
        )
        lecturas.append({'tipo': 'tension', 'canal': canal, 'valor': valor})

    if not lecturas:
        return

    usuario = dispositivo.establecimiento.usuario
    group   = f'user_{usuario.id}'
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        group,
        {
            'type':      'send_telemetria',
            'mac':       mac,
            'lecturas':  lecturas,
            'timestamp': timestamp,
        }
    )
    print(f'[MQTT] ✔ {mac} → t={t_values}  v={v_values}')


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
