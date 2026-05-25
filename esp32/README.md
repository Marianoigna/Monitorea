# ESP32 — Código IoT

Este directorio contiene el código Arduino para la placa ESP32 que actúa como
sensor IoT en el sistema de control de temperaturas.

## Sketch: `temp_mqtt/temp_mqtt.ino`

Lee la temperatura de un sensor **DS18B20** y la publica al broker MQTT público
`broker.emqx.io` en el topic `temperatura_prueba`. El backend Django recibe
los datos a través del cliente MQTT integrado (`mqtt_client.py`).

### Hardware requerido

| Componente | Descripción |
|-----------|-------------|
| ESP32 | Placa principal (cualquier variante) |
| DS18B20 | Sensor de temperatura One-Wire |
| Resistencia 4.7kΩ | Pull-up entre DATA y 3.3V |

**Conexiones:**
```
ESP32 GPIO4  ──── DATA (pin amarillo DS18B20)
ESP32 3.3V   ──┬─ VCC  (pin rojo DS18B20)
               └─ (extremo de la resistencia 4.7kΩ)
ESP32 GND    ──── GND  (pin negro DS18B20)
```

### Dependencias (Arduino Library Manager)

| Librería | Autor | Descripción |
|---------|-------|-------------|
| **PubSubClient** | Nick O'Leary | Cliente MQTT sobre TCP |
| **OneWire** | Paul Stoffregen | Bus One-Wire para DS18B20 |
| **DallasTemperature** | Miles Burton | Lectura del sensor DS18B20 |
| **ArduinoJson** | Benoit Blanchon | Serialización JSON del payload |

### Configuración

Editar `temp_mqtt.ino` y ajustar:

```cpp
const char* WIFI_SSID       = "TU_RED_WIFI";
const char* WIFI_PASSWORD   = "TU_CONTRASEÑA";
const char* SENSOR_ID       = "heladera_01";   // Nombre del sensor en el dashboard
const unsigned long INTERVALO_MS = 10000;       // Publicar cada 10 s
```

### Payload MQTT publicado

```json
{"sensor_id": "heladera_01", "valor": 4.5}
```

El servidor Django persiste automáticamente el dato y actualiza el dashboard
en tiempo real vía WebSocket.
