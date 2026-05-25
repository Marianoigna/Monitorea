"""
mqtt_subscriber.py
==================
Se conecta al broker MQTT público de EMQX (broker.emqx.io),
escucha el topic 'temperatura_prueba' en el puerto 1883
y reenvía cada lectura a la API REST de Django para que
se guarde en SQLite3 y se actualice en tiempo real vía WebSocket.

──────────────────────────────────────────────────────────────
CONFIGURACIÓN EN MQTTX (aplicación de escritorio):
──────────────────────────────────────────────────────────────
  1. Nueva conexión:
       - Host:     broker.emqx.io
       - Port:     1883
       - Protocol: MQTT
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
import requests
import paho.mqtt.client as mqtt

# ── CONFIG ────────────────────────────────────────────────────────────────────
MQTT_BROKER   = '127.0.0.1'          # Broker local Mosquitto
MQTT_PORT     = 1883                 # Puerto TCP estándar (sin SSL)
MQTT_TOPIC    = 'temperatura_prueba' # Topic que escucha este subscriber
MQTT_USER     = ''                   # Sin autenticación en broker público
MQTT_PASSWORD = ''

API_URL       = 'http://127.0.0.1:8000/api/temperatura/'
SENSOR_ID     = 'sensor_01'          # ID por defecto si el payload no lo incluye
# ─────────────────────────────────────────────────────────────────────────────


def on_connect(client, userdata, flags, reason_code, properties):
    print(f'[MQTT] Conectado al broker {MQTT_BROKER}:{MQTT_PORT}')
    client.subscribe(MQTT_TOPIC)
    print(f'[MQTT] Suscrito al topic: {MQTT_TOPIC}')


def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8').strip()
    print(f'[MQTT] Mensaje recibido: {payload}')

    try:
        # El sensor puede enviar solo el número ("23.5")
        # o un JSON ({"valor": 23.5, "sensor_id": "sensor_01"})
        try:
            data = json.loads(payload)
            valor     = float(data.get('valor', data))
            sensor_id = data.get('sensor_id', SENSOR_ID)
        except (json.JSONDecodeError, TypeError):
            valor     = float(payload)
            sensor_id = SENSOR_ID

        # Enviar a la API REST de Django
        response = requests.post(API_URL, json={
            'valor':     valor,
            'sensor_id': sensor_id,
        }, timeout=5)

        if response.status_code == 201:
            print(f'[API]  ✔ Guardado: {sensor_id} → {valor}°C')
        else:
            print(f'[API]  ✘ Error {response.status_code}: {response.text}')

    except ValueError as e:
        print(f'[ERROR] No se pudo parsear el valor: {payload} — {e}')
    except requests.RequestException as e:
        print(f'[ERROR] No se pudo conectar a la API: {e}')


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

    client.on_connect = on_connect
    client.on_message = on_message

    print(f'[MQTT] Conectando a {MQTT_BROKER}:{MQTT_PORT} ...')
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_forever()


if __name__ == '__main__':
    main()
