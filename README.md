# MONITOREA

Plataforma IoT multi-usuario para **monitoreo de sensores en tiempo real**.  
Los datos llegan desde sensores físicos (o simuladores MQTTX) a través de MQTT, se persisten en base de datos y se visualizan instantáneamente en dashboards personalizados por usuario y ubicación — sin recargar la página.

> **Estado del proyecto:** en desarrollo activo.  
> La arquitectura está diseñada para escalar en [Render](https://render.com) con autenticación, dashboards por usuario, reportes históricos y sistema de alertas configurables.

---

## Flujo de datos completo

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FUENTES DE DATOS                             │
│                                                                     │
│   [Sensor físico]        [MQTTX (simulador)]                        │
│         │                        │                                  │
│         └──────────┬─────────────┘                                  │
│                    │  MQTT sobre WebSocket SSL                       │
│                    │  broker.emqx.io : 8084                         │
│                    │  topics: temperatura_prueba / voltaje_prueba    │
└────────────────────┼────────────────────────────────────────────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │  mqtt_subscriber.py │  ← proceso separado, corre en paralelo
          │  (puente MQTT→HTTP) │
          └─────────┬───────────┘
                    │  POST /api/temperatura/
                    │  POST /api/voltaje/
                    ▼
          ┌─────────────────────┐
          │   Django REST API   │  ← app DASHBOARD
          │   (DRF APIView)     │
          └────────┬────────────┘
                   │
          ┌────────┴────────────────────────┐
          │                                 │
          ▼                                 ▼
   ┌─────────────┐               ┌─────────────────────┐
   │  SQLite3    │               │  Django Channels     │
   │ (db.sqlite3)│               │  (Channel Layer)     │
   │ persistencia│               │  group_send()        │
   └─────────────┘               └──────────┬──────────┘
                                            │  WebSocket
                                            │  ws://host/ws/temperatura/
                                            │  ws://host/ws/voltaje/
                                            ▼
                                  ┌─────────────────────┐
                                  │   Navegador del      │
                                  │   usuario            │
                                  │   dashboard.html     │
                                  │   (JS vanilla +      │
                                  │    Chart.js)         │
                                  └─────────────────────┘
```

---

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | Django 6 + Django REST Framework |
| Servidor ASGI | Daphne |
| WebSockets | Django Channels + InMemoryChannelLayer |
| MQTT | paho-mqtt (WSS · broker.emqx.io:8084) |
| Base de datos | SQLite3 (dev) → PostgreSQL (producción) |
| Frontend | HTML + CSS + JavaScript vanilla + Chart.js |
| Deploy | Render.com |

---

## Estructura del proyecto

```
Monitorea/                          ← raíz del repositorio
│
├── CORE/                           ← todo el código Django activo
│   ├── manage.py
│   ├── mqtt_subscriber.py          ← proceso puente MQTT → API REST
│   ├── db.sqlite3                  ← base de datos local
│   │
│   ├── MONITOREA/                  ── configuración del proyecto ──
│   │   ├── settings.py             ← apps, BD, channels, static
│   │   ├── urls.py                 ← rutas raíz del proyecto
│   │   ├── asgi.py                 ← entry point ASGI (HTTP + WebSocket)
│   │   └── wsgi.py
│   │
│   ├── ACCOUNTS/                   ── 🔐 autenticación ──
│   │   ├── models.py               ← (a desarrollar) perfil de usuario
│   │   ├── views.py                ← (a desarrollar) login / registro
│   │   └── urls.py                 ← /accounts/...
│   │
│   ├── DASHBOARD/                  ── 📊 tiempo real ──
│   │   ├── models.py               ← Temperatura, Voltaje
│   │   ├── views.py                ← API REST + vista HTML dashboard
│   │   ├── consumers.py            ← WebSocket consumers
│   │   ├── serializers.py          ← serializers DRF
│   │   ├── routing.py              ← rutas WebSocket
│   │   ├── urls.py                 ← /  /api/temperatura/  /api/voltaje/
│   │   ├── mqtt_client.py          ← cliente MQTT alternativo (integrado)
│   │   ├── migrations/
│   │   └── templates/DASHBOARD/
│   │       └── dashboard.html      ← UI tiempo real
│   │
│   ├── REPORTES/                   ── 📈 históricos ──
│   │   ├── models.py               ← (a desarrollar)
│   │   ├── views.py                ← (a desarrollar) filtros por fecha/sensor
│   │   └── urls.py                 ← /reportes/...
│   │
│   └── ALERTAS/                    ── 🔔 alertas ──
│       ├── models.py               ← (a desarrollar) umbrales por sensor
│       ├── views.py                ← (a desarrollar) CRUD de reglas
│       └── urls.py                 ← /alertas/...
│
├── venv/                           ← entorno virtual Python (no en git)
├── requirements.txt
├── levantar_servidor.bat           ← inicio rápido en Windows
├── activar_entorno.bat
├── Dockerfile
├── docker-compose.yml
├── render.yaml                     ← configuración de deploy en Render
└── build_render.sh / start_web.sh  ← scripts de build y arranque en Render
```

---

## Apps del proyecto

### 🔐 ACCOUNTS — Autenticación y perfiles
> **Estado:** estructura creada · en desarrollo

Gestiona el acceso a la plataforma.

| Qué hace | Detalle |
|----------|---------|
| Login / logout | Sesiones de usuario con Django auth |
| Registro | Creación de nuevas cuentas |
| Perfiles | Datos del usuario, roles y permisos |
| Multi-tenant | Cada usuario ve solo sus propios dashboards |

**Rutas:** `/accounts/login/` · `/accounts/logout/` · `/accounts/registro/`

---

### 📊 DASHBOARD — Monitoreo en tiempo real
> **Estado:** funcional ✅

Es el corazón de la aplicación. Recibe datos de sensores vía API REST, los persiste y los retransmite en tiempo real a todos los navegadores conectados mediante WebSockets.

```
Flujo interno de esta app:

  POST /api/temperatura/
         │
         ▼
   TemperaturaAPIView          VoltajeAPIView
         │                          │
    guarda en BD            guarda en BD
         │                          │
    group_send()            group_send()
         │                          │
         └──────────┬───────────────┘
                    ▼
           TemperaturaConsumer / VoltajeConsumer
                    │
            WebSocket → navegador
```

| Archivo | Responsabilidad |
|---------|-----------------|
| `models.py` | `Temperatura(valor, sensor_id, timestamp)` · `Voltaje(valor, sensor_id, timestamp)` |
| `views.py` | `GET/POST /api/temperatura/` · `GET/POST /api/voltaje/` · vista HTML |
| `consumers.py` | `TemperaturaConsumer` · `VoltajeConsumer` (async WebSocket) |
| `serializers.py` | Serialización DRF de ambos modelos |
| `routing.py` | `ws/temperatura/` · `ws/voltaje/` |
| `dashboard.html` | Gráfico Chart.js · actualización automática · reconexión WS |

**Rutas HTTP:** `/` · `/api/temperatura/` · `/api/voltaje/`  
**Rutas WebSocket:** `ws://host/ws/temperatura/` · `ws://host/ws/voltaje/`

---

### 📈 REPORTES — Historial de lecturas
> **Estado:** estructura creada · en desarrollo

Permite consultar el historial de valores de cualquier sensor aplicando filtros.

| Qué hará | Detalle |
|----------|---------|
| Filtrar por fecha | Rango desde/hasta |
| Filtrar por sensor | Por `sensor_id` o ubicación |
| Exportar | CSV / PDF (planificado) |
| Gráficos históricos | Evolución de valores en el tiempo |

**Rutas:** `/reportes/` · `/reportes/exportar/`

---

### 🔔 ALERTAS — Configuración de umbrales
> **Estado:** estructura creada · en desarrollo

Permite definir reglas por sensor para disparar notificaciones cuando un valor supera o cae por debajo de un umbral.

| Qué hará | Detalle |
|----------|---------|
| Reglas por sensor | Umbral mínimo y máximo por `sensor_id` |
| Notificaciones | Email / Twilio SMS (ya en `requirements.txt`) |
| Historial de alertas | Registro de cuándo se activó cada regla |
| Vista de configuración | CRUD de reglas desde el navegador |

**Rutas:** `/alertas/` · `/alertas/nueva/` · `/alertas/historial/`

---

### ⚙️ MONITOREA/ — Configuración del proyecto

| Archivo | Qué hace |
|---------|----------|
| `settings.py` | BD, apps instaladas, channels, static, variables de entorno |
| `urls.py` | Enruta `/` → DASHBOARD · `/accounts/` → ACCOUNTS · `/reportes/` → REPORTES · `/alertas/` → ALERTAS |
| `asgi.py` | Divide el tráfico: HTTP → Django · WebSocket → Channels |

---

### 🔌 mqtt_subscriber.py — Puente MQTT → API

Proceso independiente que corre en paralelo al servidor Django.  
Se conecta al broker MQTT, escucha los topics y reenvía cada mensaje a la API REST local.

```
[broker.emqx.io:8084 WSS]
        │
        │  on_message()
        ▼
  parsea payload (JSON o número plano)
        │
        ├─ topic temperatura_prueba  →  POST /api/temperatura/
        └─ topic voltaje_prueba      →  POST /api/voltaje/
```

**Variables de entorno:**

| Variable | Valor por defecto |
|----------|-------------------|
| `API_BASE_URL` | `http://127.0.0.1:8000` |
| `MQTT_AUTOSTART` | `1` en Render (inicia automático) |

---

## Instalación local

### 1. Clonar el repositorio

```bash
git clone https://github.com/Marianoigna/Monitorea.git
cd Monitorea
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
cd CORE
python manage.py migrate
```

---

## Levantar el servidor (desarrollo)

Se necesitan **dos procesos** corriendo al mismo tiempo:

### Opción A — Desde la terminal (recomendado)

**Terminal 1 — Servidor Django:**
```bash
cd CORE
..\venv\Scripts\python.exe -m daphne -b 127.0.0.1 -p 8000 MONITOREA.asgi:application
```

**Terminal 2 — MQTT Subscriber:**
```bash
cd CORE
..\venv\Scripts\python.exe mqtt_subscriber.py
```

Luego abrir: **`http://127.0.0.1:8000/`**

---

## Simular sensores con MQTTX

1. Descargar [MQTTX](https://mqttx.app/)
2. Nueva conexión con estos parámetros:

| Campo | Valor |
|-------|-------|
| Host | `broker.emqx.io` |
| Port | `8084` |
| Protocol | MQTT over WebSocket SSL (WSS) |
| SSL/TLS | activado |
| Username / Password | *(vacío)* |

3. Publicar en los topics:

| Topic | Payload de ejemplo |
|-------|--------------------|
| `temperatura_prueba` | `{"sensor_id": "sensor_01", "valor": 25.3}` |
| `voltaje_prueba` | `{"sensor_id": "voltaje_01", "valor": 220.5}` |

> También se acepta payload simple (solo el número): `25.3`

---

## API REST

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/temperatura/` | Últimas 50 lecturas de temperatura |
| `POST` | `/api/temperatura/` | Registra nueva lectura de temperatura |
| `GET` | `/api/voltaje/` | Últimas 50 lecturas de voltaje |
| `POST` | `/api/voltaje/` | Registra nueva lectura de voltaje |

**Ejemplo POST:**
```json
{
  "sensor_id": "sensor_01",
  "valor": 25.3
}
```

---

## WebSocket

| URL | Consumer | Evento enviado |
|-----|----------|----------------|
| `ws://host/ws/temperatura/` | `TemperaturaConsumer` | `{sensor_id, valor, timestamp}` |
| `ws://host/ws/voltaje/` | `VoltajeConsumer` | `{sensor_id, valor, timestamp}` |

---

## Deploy en Render

El archivo `render.yaml` configura el servicio automáticamente:

- **Build:** `bash build_render.sh` (instala dependencias y corre migraciones)
- **Start:** `bash start_web.sh` (levanta daphne + mqtt_subscriber en un solo proceso)
- **Variables de entorno generadas:** `SECRET_KEY`, `ALLOWED_HOSTS`, `MQTT_AUTOSTART`

---

## Roadmap

- [x] Dashboard tiempo real (temperatura + voltaje)
- [x] API REST con Django REST Framework
- [x] WebSockets con Django Channels
- [x] MQTT subscriber (broker público EMQ X)
- [x] Estructura multi-app escalable
- [ ] **ACCOUNTS** — login, registro, perfiles de usuario
- [ ] **DASHBOARD** — vistas por usuario y por ubicación/local
- [ ] **REPORTES** — filtros históricos, exportación CSV/PDF
- [ ] **ALERTAS** — umbrales configurables, notificaciones SMS/email
- [ ] Migración a PostgreSQL en producción
- [ ] Redis como Channel Layer en producción
