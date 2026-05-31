"""
mqtt_subscriber.py
==================
Se conecta al broker MQTT público de EMQX (broker.emqx.io) y escucha
todos los tópicos de telemetría de los nodos ESP32 registrados en Monitorea.

──────────────────────────────────────────────────────────────
TÓPICO ESPERADO (publicado por el ESP32):
──────────────────────────────────────────────────────────────
  monitorea/nodos/<MAC_ADDRESS>/telemetria

  Donde <MAC_ADDRESS> es la dirección MAC del ESP32 en formato
  AA:BB:CC:DD:EE:FF (mayúsculas, con dos puntos).

PAYLOAD (JSON):
──────────────────────────────────────────────────────────────
  {
    "t": [25.4, 28.1],   ← array de temperaturas, índice = canal
    "v": [220.5]         ← array de voltajes, índice = canal
  }

  Los arrays pueden tener cualquier cantidad de elementos según
  los sensores conectados al dispositivo.

CONFIGURACIÓN EN MQTTX (prueba desde escritorio):
──────────────────────────────────────────────────────────────
  - Host:     broker.emqx.io
  - Port:     8084
  - Protocol: MQTT over WebSocket SSL (WSS)
  - Topic:    monitorea/nodos/AA:BB:CC:DD:EE:FF/telemetria
  - Payload:  {"t": [25.4], "v": [220.5]}

VARIABLES DE ENTORNO:
──────────────────────────────────────────────────────────────
  API_BASE_URL   → URL base del servidor Django (default: http://127.0.0.1:8000)
  MQTT_BROKER    → Host del broker              (default: broker.emqx.io)
  MQTT_PORT      → Puerto del broker            (default: 8084)
  MQTT_USER      → Usuario MQTT (opcional)
  MQTT_PASSWORD  → Contraseña MQTT (opcional)

Uso:
    python mqtt_subscriber.py
"""

import json
import logging
import os
import time

import paho.mqtt.client as mqtt
import requests

from alertas import verificar_temperatura, verificar_voltaje

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

# ── CONFIG ────────────────────────────────────────────────────────────────────
MQTT_BROKER   = os.environ.get('MQTT_BROKER', 'broker.emqx.io')
MQTT_PORT     = int(os.environ.get('MQTT_PORT', '8084'))
MQTT_USER     = os.environ.get('MQTT_USER', '')
MQTT_PASSWORD = os.environ.get('MQTT_PASSWORD', '')

# Tópico wildcard: captura TODOS los nodos registrados
MQTT_TOPIC    = 'monitorea/nodos/+/telemetria'

API_BASE      = os.environ.get('API_BASE_URL', 'http://127.0.0.1:8000')
# ─────────────────────────────────────────────────────────────────────────────


def _mac_from_topic(topic: str) -> str:
    """Extrae la MAC del tópico 'monitorea/nodos/<MAC>/telemetria'."""
    parts = topic.split('/')
    return parts[2].upper()  # índice 2: AA:BB:CC:DD:EE:FF


def on_connect(client, userdata, flags, reason_code, properties):
    print(f'[MQTT] Conectado al broker {MQTT_BROKER}:{MQTT_PORT}')
    client.subscribe(MQTT_TOPIC)
    print(f'[MQTT] Suscrito a: {MQTT_TOPIC}')


def on_message(client, userdata, msg):
    topic   = msg.topic
    payload = msg.payload.decode('utf-8').strip()
    print(f'[MQTT] [{topic}] {payload}')

    try:
        mac  = _mac_from_topic(topic)
        data = json.loads(payload)
    except (IndexError, json.JSONDecodeError) as e:
        print(f'[ERROR] Tópico o payload inválido: {topic} — {e}')
        return

    t_values = data.get('t', [])
    v_values = data.get('v', [])

    # ── Reenviar a la API Django ──────────────────────────────────────────────
    api_url = f'{API_BASE}/api/telemetria/{mac}/'
    try:
        response = requests.post(
            api_url,
            json={'t': t_values, 'v': v_values},
            timeout=5,
        )
        if response.status_code == 201:
            print(f'[API]  ✔ {mac} → t={t_values}  v={v_values}')
        elif response.status_code == 404:
            print(f'[API]  ✘ Dispositivo no registrado: {mac}')
        else:
            print(f'[API]  ✘ Error {response.status_code}: {response.text}')
    except requests.RequestException as e:
        print(f'[ERROR] No se pudo conectar a la API: {e}')
        return

    # ── Verificar umbrales y alertas WhatsApp ─────────────────────────────────
    for canal, valor in enumerate(t_values):
        sensor_id = f'{mac}_t{canal}'
        alerta = verificar_temperatura(sensor_id, valor)
        if alerta:
            print(f'[ALERTA] WhatsApp enviado: {alerta}')

    for canal, valor in enumerate(v_values):
        sensor_id = f'{mac}_v{canal}'
        alerta = verificar_voltaje(sensor_id, valor)
        if alerta:
            print(f'[ALERTA] WhatsApp enviado: {alerta}')


def main():
    retry_delay = 5

    while True:
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport='websockets')
            client.tls_set()  # SSL para WSS (puerto 8084)

            if MQTT_USER:
                client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

            client.on_connect = on_connect
            client.on_message = on_message

            print(f'[MQTT] Conectando a {MQTT_BROKER}:{MQTT_PORT} ...')
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            client.loop_forever()

        except Exception as e:
            print(f'[MQTT] Error de conexión: {type(e).__name__}: {e}')
            print(f'[MQTT] Reintentando en {retry_delay}s...')
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)


if __name__ == '__main__':
    main()
