# MONITOREA

> Plataforma IoT multi-usuario para **monitoreo de sensores en tiempo real**.  
> Los datos llegan desde sensores físicos (o simuladores MQTTX) a través de MQTT, se persisten en base de datos y se visualizan instantáneamente en dashboards personalizados — sin recargar la página.

```
╔══════════════════════════════════════════════════════════════════════╗
║                    ESTADO ACTUAL DEL PROYECTO                       ║
╠══════════════════════╦═══════════════════════════════════════════════╣
║  ✅  Landing page     ║  Página pública de bienvenida en /           ║
║  ✅  Autenticación    ║  Login · Registro · Logout · CustomUser       ║
║  ✅  Dashboard RT     ║  Temperatura + Voltaje en tiempo real         ║
║  ✅  MQTT bridge      ║  Suscriptor autónomo → API REST               ║
║  ✅  Control acceso   ║  @requiere_premium · redirect a planes        ║
║  ✅  Página de planes ║  Vista intermediaria con cards Gratis/Premium ║
║  ✅  MercadoPago      ║  Checkout Pro (modo TEST)                     ║
║  🔄  Reportes         ║  Protegido · template pendiente               ║
║  🔄  Alertas          ║  Protegido · template pendiente               ║
║  🔄  PostgreSQL       ║  SQLite en dev → Postgres en producción       ║
╚══════════════════════╩═══════════════════════════════════════════════╝
```

---

## Modelo de negocio y niveles de acceso

```
╔═════════════════════════════════════════════════════════════════════════╗
║                         NIVELES DE USUARIO                             ║
╠══════════════════════════════╦══════════════════════════════════════════╣
║     ANÓNIMO (sin login)      ║  GRATUITO (logueado, sin plan activo)   ║
║                              ║                                         ║
║  ✅ Landing page              ║  ✅ Dashboard tiempo real               ║
║  ✅ Botón "Iniciar sesión"    ║  ✅ Ver sus sensores en vivo            ║
║  ❌ Todo lo demás             ║  ❌ Reportes históricos                 ║
║                              ║  ❌ Configurar alertas                  ║
╠══════════════════════════════╩═════════════════════╦════════════════════╣
║               PREMIUM (suscripción activa)         ║                   ║
║                                                    ║                   ║
║  ✅ Dashboard tiempo real                          ║                   ║
║  ✅ Reportes históricos (filtros por fecha/sensor) ║                   ║
║  ✅ Configurar alertas (umbrales + notificaciones) ║                   ║
║  ✅ Notificaciones SMS/email vía Twilio            ║                   ║
╚════════════════════════════════════════════════════╩════════════════════╝
```

### Flujo de acceso completo

```
  ┌─────────────────┐
  │   / (Landing)   │  ← página pública, sin login
  │   Bienvenido a  │
  │    MONITOREA    │
  └────────┬────────┘
           │  click "Iniciar sesión"
           ▼
  ┌─────────────────┐
  │ /accounts/login │
  └────────┬────────┘
           │  credenciales OK
           ▼
  ┌─────────────────┐
  │  /dashboard/    │  ← dashboard tiempo real
  │  🍔 menú lateral│
  │  Reportes       │
  │  Alertas        │
  │  Cerrar sesión  │
  └────────┬────────┘
           │
     ┌─────┴──────┐
     │  click en  │
     │  Reportes  │
     │  o Alertas │
     └─────┬──────┘
           │
     ┌─────▼──────────────────────────────┐
     │    @requiere_premium               │
     │    ¿tiene_premium_activo()?        │
     └─────┬──────────────────────────────┘
           │
     ┌─────┴──────┐          ┌──────────────┐
     │    SÍ      │          │      NO      │
     │  (premium) │          │  (gratuito)  │
     └─────┬──────┘          └──────┬───────┘
           │                        │
           ▼                        ▼
   Vista solicitada       /suscripciones/planes/
   (Reportes / Alertas)   ┌────────────────────┐
                          │ 🔒 Acceso restringido│
                          │                    │
                          │ GRATUITO  PREMIUM  │
                          │  $0        $4.999  │
                          │ (actual) [Contratar]│
                          └─────────┬──────────┘
                                    │  click "Contratar ahora"
                                    ▼
                          /suscripciones/checkout-prueba/
                                    │
                                    ▼
                          ┌──────────────────────┐
                          │  MercadoPago         │
                          │  Checkout Pro (TEST) │
                          └──────────────────────┘
```

### Control de acceso en el código

El decorator `@requiere_premium` en [SUSCRIPCIONES/decorators.py](CORE/SUSCRIPCIONES/decorators.py) protege automáticamente cualquier vista:

```python
from SUSCRIPCIONES.decorators import requiere_premium

@requiere_premium          # ← una sola línea bloquea la vista
def mi_vista(request):
    ...
```

Si el usuario no tiene plan activo → mensaje de advertencia + redirect a `/suscripciones/planes/`.

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
| Pagos | MercadoPago SDK (Checkout Pro) |
| Notificaciones | Twilio (WhatsApp / SMS) |
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
│   ├── MONITOREA/                  ── ⚙️  configuración del proyecto ──
│   │   ├── settings.py             ← apps, BD, channels, static, dotenv
│   │   ├── urls.py                 ← rutas raíz del proyecto
│   │   ├── asgi.py                 ← entry point ASGI (HTTP + WebSocket)
│   │   └── wsgi.py
│   │
│   ├── ACCOUNTS/                   ── 🔐 autenticación ── ✅ funcional
│   │   ├── models.py               ← CustomUser (is_premium, premium_until)
│   │   ├── views.py                ← login_view · logout_view · register
│   │   ├── forms.py                ← LoginForm · RegisterForm
│   │   ├── urls.py                 ← /accounts/login/ · /logout/ · /registro/
│   │   └── templates/ACCOUNTS/
│   │       ├── login.html
│   │       └── register.html
│   │
│   ├── SUSCRIPCIONES/              ── 💳 pagos y control de acceso ── ✅ funcional
│   │   ├── models.py               ← Plan · Suscripcion · Pago
│   │   ├── decorators.py           ← @requiere_premium
│   │   ├── views.py                ← planes() · checkout_pro_prueba() · webhook
│   │   ├── urls.py                 ← /planes/ · /checkout-prueba/ · /webhook/
│   │   ├── migrations/
│   │   └── templates/SUSCRIPCIONES/
│   │       └── planes.html         ← cards Gratuito / Premium + botón MP
│   │
│   ├── DASHBOARD/                  ── 📊 tiempo real ── ✅ funcional
│   │   ├── models.py               ← Temperatura · Voltaje
│   │   ├── views.py                ← landing() · dashboard() · API REST
│   │   ├── consumers.py            ← TemperaturaConsumer · VoltajeConsumer
│   │   ├── serializers.py
│   │   ├── routing.py              ← ws/temperatura/ · ws/voltaje/
│   │   ├── urls.py                 ← / · /dashboard/ · /api/...
│   │   ├── mqtt_client.py
│   │   ├── migrations/
│   │   └── templates/DASHBOARD/
│   │       ├── landing.html        ← página pública de bienvenida
│   │       └── dashboard.html      ← UI tiempo real + menú hamburguesa
│   │
│   ├── REPORTES/                   ── 📈 históricos  🔒 premium ── 🔄 en desarrollo
│   │   ├── views.py                ← @requiere_premium · (template pendiente)
│   │   └── urls.py                 ← /reportes/
│   │
│   └── ALERTAS/                    ── 🔔 alertas  🔒 premium ── 🔄 en desarrollo
│       ├── views.py                ← @requiere_premium · (template pendiente)
│       └── urls.py                 ← /alertas/
│
├── .env                            ← credenciales reales (NO en git)
├── venv/                           ← entorno virtual Python (NO en git)
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

### 💳 SUSCRIPCIONES — Planes, pagos y control de acceso
> **Estado:** ✅ funcional — MercadoPago Checkout Pro integrado (TEST)

Núcleo del modelo de negocio. Determina qué puede hacer cada usuario.

```
  Plan
  ├── gratuito  (precio: $0)        → solo DASHBOARD
  └── premium   (precio: $4.999/mes) → DASHBOARD + REPORTES + ALERTAS

  CustomUser (en ACCOUNTS)
  ├── is_premium       BooleanField  ← flag directo
  ├── premium_until    DateTimeField ← fecha de vencimiento
  └── tiene_premium_activo()        ← devuelve True si is_premium AND premium_until > now

  Pago
  ├── suscripcion ──► (FK) Suscripcion
  ├── monto
  ├── metodo          # 'mercadopago'
  ├── referencia_gateway
  └── exitoso
```

**Rutas disponibles:**

| URL | Vista | Descripción |
|-----|-------|-------------|
| `/suscripciones/planes/` | `planes` | 🔒 Login requerido · cards Gratis/Premium |
| `/suscripciones/checkout-prueba/` | `checkout_pro_prueba` | Genera preferencia MP y redirige |
| `/suscripciones/webhook/` | `webhook` | Recibe notificaciones de MP |
| `/suscripciones/pago-exitoso/` | `pago_exitoso` | Pantalla de confirmación |
| `/suscripciones/pago-fallido/` | `pago_fallido` | Pantalla de error |

**Integración MercadoPago:**
```python
# checkout_pro_prueba usa solo ACCESS_TOKEN (no requiere PLAN_ID)
sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
preference_data = {
    "items": [{"title": "Suscripción Premium", "quantity": 1, "unit_price": 4999}],
    "back_urls": {"success": ..., "failure": ..., "pending": ...},
    "auto_return": "approved"
}
```

| Archivo | Responsabilidad |
|---------|----------------|
| `models.py` | `Plan` · `Suscripcion` · `Pago` |
| `decorators.py` | `@requiere_premium` → redirect a `/suscripciones/planes/` |
| `views.py` | `planes()` · `checkout_pro_prueba()` · `webhook()` |
| `templates/planes.html` | Cards Gratuito/Premium + botón "Contratar ahora" |

---

### 🔐 ACCOUNTS — Autenticación y perfiles
> **Estado:** ✅ funcional

Gestiona el acceso a la plataforma con un modelo `CustomUser` extendido.

```python
class CustomUser(AbstractUser):
    is_premium    = BooleanField(default=False)
    premium_until = DateTimeField(null=True, blank=True)

    def tiene_premium_activo(self):
        return (
            self.is_premium
            and self.premium_until is not None
            and self.premium_until > timezone.now()
        )
```

| Qué hace | Detalle |
|----------|---------|
| Login | `POST /accounts/login/` → redirect a `/dashboard/` |
| Logout | `GET /accounts/logout/` → redirect a `/accounts/login/` |
| Registro | `POST /accounts/registro/` |
| Premium check | `CustomUser.tiene_premium_activo()` |

**Usuario de prueba premium:**

| Usuario | Contraseña | Plan | Acceso |
|---------|-----------|------|--------|
| `PruebaPremium` | `premium1234` | Premium activo (365 días) | Todo |
| `Prueba` | *(cualquiera)* | Gratuito | Solo dashboard |

**Rutas:** `/accounts/login/` · `/accounts/logout/` · `/accounts/registro/`

---

### 📊 DASHBOARD — Monitoreo en tiempo real
> **Estado:** ✅ funcional

Contiene tanto la landing page pública como el dashboard protegido con WebSockets.

```
  /  (landing.html)           ← pública, sin login
  /dashboard/  (dashboard.html) ← @login_required

  Flujo interno del dashboard:

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
            WebSocket → navegador (Chart.js)
```

**Menú lateral (hamburguesa) en dashboard.html:**
```
  🍔  ← click para abrir
  ┌──────────────────┐
  │  📊 Dashboard    │  → /dashboard/
  │  📈 Reportes     │  → /reportes/
  │  🔔 Alertas      │  → /alertas/
  │  ──────────────  │
  │  🚪 Cerrar sesión│  → /accounts/logout/
  └──────────────────┘
```

| Archivo | Responsabilidad |
|---------|-----------------|
| `models.py` | `Temperatura(valor, sensor_id, timestamp)` · `Voltaje(valor, sensor_id, timestamp)` |
| `views.py` | `landing()` · `dashboard()` · `GET/POST /api/temperatura/` · `GET/POST /api/voltaje/` |
| `consumers.py` | `TemperaturaConsumer` · `VoltajeConsumer` (async WebSocket) |
| `serializers.py` | Serialización DRF de ambos modelos |
| `routing.py` | `ws/temperatura/` · `ws/voltaje/` |
| `landing.html` | Bienvenida pública · feature cards · botón login |
| `dashboard.html` | Gráficos Chart.js · WebSocket · menú hamburguesa |

**Rutas HTTP:** `/` · `/dashboard/` · `/api/temperatura/` · `/api/voltaje/`  
**Rutas WebSocket:** `ws://host/ws/temperatura/` · `ws://host/ws/voltaje/`

---

### 📈 REPORTES — Historial de lecturas 🔒
> **Estado:** 🔄 estructura creada · protegida con `@requiere_premium` · template pendiente

Disponible solo para usuarios con suscripción premium activa.

| Qué hará | Detalle |
|----------|---------|
| Filtrar por fecha | Rango desde/hasta |
| Filtrar por sensor | Por `sensor_id` o ubicación |
| Exportar | CSV / PDF (planificado) |
| Gráficos históricos | Evolución de valores en el tiempo |

**Rutas:** `/reportes/` · `/reportes/exportar/`

---

### 🔔 ALERTAS — Configuración de umbrales 🔒
> **Estado:** 🔄 estructura creada · protegida con `@requiere_premium` · template pendiente

Disponible solo para usuarios con suscripción premium activa.

| Qué hará | Detalle |
|----------|---------|
| Reglas por sensor | Umbral mínimo y máximo por `sensor_id` |
| Notificaciones | WhatsApp/SMS vía Twilio (variables en `.env`) |
| Historial de alertas | Registro de cuándo se activó cada regla |
| Vista de configuración | CRUD de reglas desde el navegador |

**Rutas:** `/alertas/` · `/alertas/nueva/` · `/alertas/historial/`

---

### ⚙️ MONITOREA/ — Configuración del proyecto

| Archivo | Qué hace |
|---------|----------|
| `settings.py` | BD, apps, channels, static, `load_dotenv()`, `AUTH_USER_MODEL` |
| `urls.py` | `/` → DASHBOARD · `/dashboard/` → DASHBOARD · `/accounts/` → ACCOUNTS · `/suscripciones/` → SUSCRIPCIONES · `/reportes/` → REPORTES · `/alertas/` → ALERTAS |
| `asgi.py` | Divide el tráfico: HTTP → Django · WebSocket → Channels |
> **Estado:** estructura creada · protegida con `@requiere_premium` · template pendiente

Disponible solo para usuarios con suscripción premium activa.

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
| `urls.py` | `/` → DASHBOARD · `/accounts/` → ACCOUNTS · `/suscripciones/` → SUSCRIPCIONES · `/reportes/` → REPORTES · `/alertas/` → ALERTAS |
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

## Variables de entorno

Creá un archivo `.env` en la raíz del proyecto (nunca lo subas al repositorio):

```bash
# Django
SECRET_KEY=django-insecure-cambia-esto-en-produccion
DEBUG=True
API_BASE_URL=http://127.0.0.1:8000

# Twilio (alertas WhatsApp/SMS)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+549XXXXXXXXXX

# Umbrales de alertas
TEMP_MAX=8.0
TEMP_MIN=-25.0
VOLT_MAX=240.0
VOLT_MIN=190.0
ALERT_COOLDOWN_SEGUNDOS=300

# MercadoPago (credenciales TEST del panel de desarrolladores)
MERCADOPAGO_PUBLIC_KEY=TEST-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MERCADOPAGO_ACCESS_TOKEN=TEST-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MERCADOPAGO_BACK_URL=http://localhost:8000/
```

> Las credenciales TEST de MercadoPago se obtienen en:  
> https://www.mercadopago.com.ar/developers/panel → Credenciales de prueba

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

```
╔══════════════════════════════════════════════════════════════════════╗
║                          PROGRESO                                   ║
╠══════════╦═══════════════════════════════════════════════════════════╣
║    ✅    ║  Dashboard tiempo real (temperatura + voltaje)            ║
║    ✅    ║  API REST con Django REST Framework                       ║
║    ✅    ║  WebSockets con Django Channels                           ║
║    ✅    ║  MQTT subscriber (broker público EMQ X)                   ║
║    ✅    ║  Estructura multi-app escalable                           ║
║    ✅    ║  ACCOUNTS — login, registro, logout, CustomUser           ║
║    ✅    ║  Landing page pública en /                                ║
║    ✅    ║  Menú hamburguesa en dashboard                            ║
║    ✅    ║  @requiere_premium — protección de vistas                 ║
║    ✅    ║  Página de planes (/suscripciones/planes/)                ║
║    ✅    ║  MercadoPago Checkout Pro (modo TEST)                     ║
║    🔄    ║  REPORTES — templates y lógica de filtros                 ║
║    🔄    ║  ALERTAS — templates y configuración de umbrales          ║
║    🔄    ║  Webhook MP → activar plan automáticamente                ║
║    🔄    ║  Dashboards por usuario y ubicación/local                 ║
║    🔄    ║  Exportación CSV/PDF en reportes                          ║
║    🔄    ║  PostgreSQL en producción                                 ║
║    🔄    ║  Redis como Channel Layer en producción                   ║
╚══════════╩═══════════════════════════════════════════════════════════╝
```
