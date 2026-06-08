Instrucciones para Copilot en Monitorea (Web App IoT)
Este documento guía a Copilot para generar código consistente con la arquitectura, convenciones y objetivos de Monitorea, una plataforma IoT multiusuario basada en Django, Django REST Framework y Django Channels, con un puente MQTT y funcionalidades de suscripción/pago.

Propósito
Asegurar coherencia de estilos, estructuras y patrones de diseño entre componentes backend (API REST, WebSockets, streaming), MQTT bridge y lógica de negocio (multiusuario, premium, alertas).
Facilitar la expansión de endpoints, sensores y dashboards sin romper el flujo actual.
Mantener buenas prácticas de seguridad, pruebas y despliegue.
Contexto y arquitectura relevante (extraído del README)
Backend principal: Django 6 + Django REST Framework; servidor ASGI (Daphne).
WebSockets: Django Channels + InMemoryChannelLayer; agrupación por usuario: group_send("user_<id>").
Puente MQTT: mqtt_subscriber.py, proceso separado que envía telemetría a la API REST local.
Multiusuario aislado: cada usuario ve solo sus dispositivos y telemetría.
Recursos principales: ACCOUNTS (CustomUser con is_premium, premium_until), SUSCRIPCIONES (planes, pagos, decorators.requiere_premium), DASHBOARD (telemetría en tiempo real), REPORTES, ALERTAS.
Frontend básico: HTML/JS con Chart.js (sin SPA compleja).
Entorno: .env para secretos (no en git), compatibilidad con Render/render.yaml.
Convenciones de código y estilo
Python 3.x con type hints cuando aporte claridad.
Estilo PEP8, nombres claros y consistentes (snake_case para Python, CamelCase para clases).
Docstrings en formato Google o reStructuredText; comentarios claros.
Nombres de módulos y funciones reflejan su rol (ej. mqtt_subscriber.py, TemperaturaAPIView, TelemetriaSerializer).
URLs y rutas explícitas, siguiendo el diccionario de rutas del README.
Seguridad: no incrustar secretos; acceder a variables desde .env; validar entradas; manejar autenticación y permisos correctamente.
Tests: cubrir endpoints DRF, consumidores de WebSocket y decoradores.
Plantillas y patrones para Copilot
1) Crear un nuevo endpoint DRF para un modelo existente
Prompt esperado:
Crear un APIView/ModelViewSet para el modelo X con:
GET: listar los últimos N registros (p. ej., 50)
POST: crear registro con validación básica
Permisos: autenticación y permisos de usuario
Incluir serializers.py correspondiente y routing en urls.py
Incluir tests unitarios básicos (verificar 200/201)
Salida deseada: Modelo existente, Serializer, APIView o ViewSet, URL conf, Tests
2) Añadir decorador de premium a una vista existente
Prompt esperado:
Aplicar @requiere_premium a la vista mi_vista en una app existente.
Si no tiene premium, redirigir a /suscripciones/planes/ y mostrar mensaje.
Mantener compatibilidad con DRF si fuera una APIView.
Salida deseada: Import y uso del decorador, comentarios explicativos.
3) Crear un nuevo Consumer de WebSocket para un sensor
Prompt esperado:
Crear TemperaturaConsumer que lea de channel layer, asuma grupo "user_<id>"
Permisos: autenticación y correcta asociación de usuario
Enviar mensajes al frontend en formato JSON: { sensor_id, valor, timestamp }
Salida deseada: Clase Consumer (async), métodos connect/disconnect/receive, grupo de usuarios correcto, estructura JSON.
4) Añadir un nuevo endpoint de telemetría POST
Prompt esperado:
POST /api/telemetria/<mac>/ con payload { t: [values], v: [values] } u otros formatos compatibles
Validar mac, asociar a dispositivo del usuario, persistir telemetría y notificar consumidores
Salida deseada: APIView/Serializer, lógica de validación, llamadas a group_send("user_<id>").
5) Añadir lógica de configuración de alertas básica
Prompt esperado:
Crear una vista para crear/editar reglas de alerta por sensor
Acceso: premium
Persistencia en modelo ConfiguracionAlerta
Salida deseada: Modelo, Serializer, View, URL; decorador de premium aplicado.
Reglas generales para prompts de Copilot
Especifica la capa exacta: models.py, serializers.py, views.py, consumers.py, routing.py, templates, urls.py, pruebas.
Indica claramente permisos y esquemas de autenticación esperados.
Indica formatos de entrada y salida para APIs y websockets.
Pide pruebas unitarias y/o de integración básicas cuando corresponda.
Pide comentarios/docstrings breves en los archivos generados.
Mantén consistencia con el estilo y las convenciones descritas en este documento y en el README.
Estructura de archivos y puntos de integración a respetar
Apps principales y sus responsabilidades:
ACCOUNTS: autenticación, CustomUser, login/registro
SUSCRIPCIONES: planes, decoración @requiere_premium
DASHBOARD: telemetría, consumo, endpoints API, consumidores WS
REPORTES: historia y exportación (pendiente)
ALERTAS: umbrales y notificaciones (premium)
Interacciones clave:
MQTT bridge (mqtt_subscriber.py) envía a /api/telemetria/<mac> o endpoints de telemetría
Telemetría se guarda y se empuja a WebSocket con group_send("user_<id>")
Las vistas protegidas deben respetar @login_required o permisos de usuario
Nombres y rutas clave:
Endpoints: /api/temperatura/, /api/voltaje/
WebSocket: ws://host/ws/temperatura/, ws://host/ws/voltaje/
Decorador premium: SUSCRIPCIONES/decorators.py
Guía de pruebas y validaciones
Propuesta mínima de tests:
Pruebas de endpoints DRF (GET/POST)
Pruebas del decorator @requiere_premium en vista protegida
Pruebas básicas de Consumer WS (conexión y recepción de mensajes)
Pruebas de integración simples: POST telemetría genera entry en DB y emite a WS
Las pruebas no deben depender de secretos reales (usa settings de pruebas o fixtures)
Documentar pruebas en tests/ con nombres claros
Seguridad y manejo de secretos
Nunca subir secrets al repo. Usa .env y load_dotenv en settings.py.
Validar entradas de API para evitar inyección.
Roles: autenticación de usuario y control de acceso por premium.
Telemetría: validar MAC y asociación al usuario propietario.
Despliegue y entorno
Varias rutas dependen del entorno (Render, PostgreSQL en producción). Mantener README y render.yaml actualizados.
Variables de entorno en .env (ejemplos en README). Copilot debe respetar estas claves.
Ejecutar pruebas: python manage.py test y pruebas de endpoints con DRF APIClient.
Plantilla de ejemplo de una nueva app o módulo
Modelo: class SensorConfig(models.Model): ...
Serializador: class SensorConfigSerializer(serializers.ModelSerializer): ...
Vista: class SensorConfigView(APIView): ...
URL: path('api/sensor-config/', SensorConfigView.as_view(), name='sensor-config')
Tests: class SensorConfigTests(TestCase): ...
Notas finales
Para un bloque concreto, describe el objetivo, las entidades involucradas y el formato de entrada/salida esperados (p. ej., JSON), y especifica el archivo donde insertarlo (por ejemplo, DASHBOARD/views.py, SUSCRIPCIONES/decorators.py, etc.).
Este documento debe ser compatible con el README existente.