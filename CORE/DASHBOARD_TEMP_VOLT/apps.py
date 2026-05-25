import os

from django.apps import AppConfig


class DashboardTempVoltConfig(AppConfig):
    name = 'DASHBOARD_TEMP_VOLT'

    def ready(self):
        # Arrancar el suscriptor MQTT en un hilo de fondo solo cuando
        # se levanta el servidor ASGI (MQTT_AUTOSTART=1).
        # Queda desactivado durante migrate, collectstatic, etc.
        if os.environ.get('MQTT_AUTOSTART') == '1':
            from . import mqtt_client
            mqtt_client.start()
