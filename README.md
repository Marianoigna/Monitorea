# Control_Temperatura

Sistema de control y monitoreo de temperaturas en **heladeras y freezers** para locales comerciales.

Integra un backend Django, un dashboard en tiempo real y código IoT para placas **ESP32**.

---

## Arquitectura

```
[ESP32 + DS18B20]
      │
      │  MQTT (broker.emqx.io:1883)
      ▼
[mqtt_client.py]  ← hilo de fondo dentro de Django
      │
      ├──► SQLite3 (persistencia)
      │
      └──► Django Channels (WebSocket)
                  │
                  ▼
          [Dashboard HTML]
        (actualización en tiempo real)
```

---

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | Django + Django REST Framework |
| WebSockets | Django Channels + Daphne (ASGI) |
| MQTT | paho-mqtt (integrado en Django) |
| Base de datos | SQLite3 |
| Frontend | HTML + CSS + JavaScript vanilla + Chart.js |
| IoT | ESP32 + DS18B20 + Arduino (PubSubClient) |

---

## Estructura del proyecto

```
Control_Temperatura/
├── CONTROL_TEMPERATURA/          # Módulo de configuración Django
│   ├── settings.py
│   ├── asgi.py
│   ├── urls.py
│   └── wsgi.py
├── DASHBOARD_TEMP_VOLT/          # App Django principal
│   ├── models.py                 # Modelos: Temperatura, Voltaje
│   ├── views.py                  # API REST + vista dashboard
│   ├── consumers.py              # WebSocket consumers
│   ├── serializers.py
│   ├── urls.py
│   ├── routing.py
│   ├── mqtt_client.py            # Suscriptor MQTT (hilo de fondo)
│   ├── apps.py
│   ├── migrations/
│   └── templates/
│       └── DASHBOARD_TEMP_VOLT/
│           └── dashboard.html    # Dashboard tiempo real
├── esp32/                        # Código IoT para ESP32
│   ├── README.md
│   └── temp_mqtt/
│       └── temp_mqtt.ino         # Sketch Arduino (DS18B20 + MQTT)
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── start_web.sh
```

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Marianoigna/Control_Temperatura.git
cd Control_Temperatura
```

### 2. Crear y activar el entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Aplicar migraciones

```bash
python manage.py migrate
```

---

## Levantar el servidor

### Opción A — Docker (recomendado)

```bash
docker-compose up --build
```

Acceder en `http://localhost:8000/`

### Opción B — Manual

**Terminal 1 — Django + MQTT:**

```bash
export DJANGO_SETTINGS_MODULE=CONTROL_TEMPERATURA.settings
export MQTT_AUTOSTART=1
python manage.py runserver
```

O con Daphne (ASGI completo con WebSockets):

```bash
MQTT_AUTOSTART=1 daphne -b 0.0.0.0 -p 8000 CONTROL_TEMPERATURA.asgi:application
```

---

## API REST

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/temperatura/` | Últimas 50 lecturas de temperatura |
| `POST` | `/api/temperatura/` | Registra nueva lectura de temperatura |
| `GET` | `/api/voltaje/` | Últimas 50 lecturas de voltaje |
| `POST` | `/api/voltaje/` | Registra nueva lectura de voltaje |

**Ejemplo POST temperatura:**
```json
{
  "sensor_id": "heladera_01",
  "valor": 4.5
}
```

---

## Dashboard

Accesible en `http://localhost:8000/`

- Temperatura y voltaje en tiempo real vía WebSocket
- Gráfico de línea con las últimas 5 lecturas de temperatura
- Gráfico de barra con el voltaje actual
- Indicador de estado de conexión con reconexión automática

---

## ESP32 — Sensor IoT

Ver `esp32/README.md` para instrucciones de hardware y configuración del sketch Arduino.

---

## Configuración MQTT

| Variable de entorno | Default | Descripción |
|--------------------|---------|-------------|
| `MQTT_BROKER` | `broker.emqx.io` | Broker MQTT |
| `MQTT_PORT` | `8084` | Puerto (WSS) |
| `MQTT_TOPIC_TEMP` | `temperatura_prueba` | Topic temperatura |
| `MQTT_TOPIC_VOLT` | `voltaje_prueba` | Topic voltaje |
| `MQTT_USER` | *(vacío)* | Usuario MQTT |
| `MQTT_PASSWORD` | *(vacío)* | Contraseña MQTT |
| `MQTT_AUTOSTART` | `0` | `1` para iniciar MQTT al levantar Django |

---

## Basado en

Este proyecto está basado en [control_heladera](https://github.com/Marianoigna/control_heladera).
