"""
mqtt_subscriber.py
==================
Se conecta al broker MQTT público de EMQX (broker.emqx.io),
escucha los topics 'temperatura_prueba' y 'voltaje_prueba' en el puerto 8084 (WebSocket SSL)
y reenvía cada lectura a la API REST de Django para que
se guarde en SQLite3 y se actualice en tiempo real vía WebSocket.

──────────────────────────────────────────────────────────────
CONFIGURACIÓN EN MQTTX (aplicación de escritorio):
──────────────────────────────────────────────────────────────
  1. Nueva conexión:
       - Host:     broker.emqx.io
       - Port:     8084
       - Protocol: MQTT over WebSocket SSL (WSS)
       - Client ID: (cualquiera, ej: mqttx_test_01)
       - Sin usuario ni contraseña

  2. Publicar mensaje:
       - Topic:   temperatura_prueba
       - QoS:     0
       - Payload (elige uno de estos formatos):

           Formato simple (solo número):
               25.3

           Formato JSON (recomendado):
               {"sensor_id": "sensor_01", "valor": 25.3}

  3. Asegúrate de que mqtt_subscriber.py esté corriendo
     antes de publicar desde MQTTX.
──────────────────────────────────────────────────────────────

Uso:
    python mqtt_subscriber.py
"""

import json
import logging
import os
import requests
import paho.mqtt.client as mqtt

from alertas import verificar_temperatura, verificar_voltaje

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

# ── CONFIG ────────────────────────────────────────────────────────────────────
MQTT_BROKER        = 'broker.emqx.io'
MQTT_PORT          = 8084
MQTT_TOPIC_TEMP    = 'temperatura_prueba'
MQTT_TOPIC_VOLT    = 'voltaje_prueba'
MQTT_USER          = ''
MQTT_PASSWORD      = ''

_API_BASE          = os.environ.get('API_BASE_URL', 'http://127.0.0.1:8000')
API_URL_TEMP       = f'{_API_BASE}/api/temperatura/'
API_URL_VOLT       = f'{_API_BASE}/api/voltaje/'
SENSOR_ID_TEMP     = 'sensor_01'
SENSOR_ID_VOLT     = 'voltaje_01'
# ─────────────────────────────────────────────────────────────────────────────


def on_connect(client, userdata, flags, reason_code, properties):
    print(f'[MQTT] Conectado al broker {MQTT_BROKER}:{MQTT_PORT}')
    client.subscribe(MQTT_TOPIC_TEMP)
    client.subscribe(MQTT_TOPIC_VOLT)
    print(f'[MQTT] Suscrito a: {MQTT_TOPIC_TEMP}, {MQTT_TOPIC_VOLT}')


def on_message(client, userdata, msg):
    topic   = msg.topic
    payload = msg.payload.decode('utf-8').strip()
    print(f'[MQTT] [{topic}] {payload}')

    is_temp = (topic == MQTT_TOPIC_TEMP)
    api_url   = API_URL_TEMP if is_temp else API_URL_VOLT
    sensor_id = SENSOR_ID_TEMP if is_temp else SENSOR_ID_VOLT
    unidad    = '°C' if is_temp else 'V'

    try:
        try:
            data = json.loads(payload)
            valor     = float(data.get('valor', data))
            sensor_id = data.get('sensor_id', sensor_id)
        except (json.JSONDecodeError, TypeError):
            valor = float(payload)

        response = requests.post(api_url, json={
            'valor':     valor,
            'sensor_id': sensor_id,
        }, timeout=5)

        if response.status_code == 201:
            print(f'[API]  ✔ Guardado: {sensor_id} → {valor}{unidad}')
        else:
            print(f'[API]  ✘ Error {response.status_code}: {response.text}')

        # ── Verificar umbrales y enviar alerta WhatsApp si corresponde ──
        if is_temp:
            alerta = verificar_temperatura(sensor_id, valor)
        else:
            alerta = verificar_voltaje(sensor_id, valor)

        if alerta:
            print(f'[ALERTA] WhatsApp enviado: {alerta}')

    except ValueError as e:
        print(f'[ERROR] No se pudo parsear el valor: {payload} — {e}')
    except requests.RequestException as e:
        print(f'[ERROR] No se pudo conectar a la API: {e}')


def main():
    import time
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
