from django.apps import AppConfig


class AlertasConfig(AppConfig):
    name = 'ALERTAS'

    def ready(self):
        from django.db.models.signals import post_save
        from DASHBOARD.models import Telemetria
        from ALERTAS.views import handle_nueva_telemetria
        post_save.connect(handle_nueva_telemetria, sender=Telemetria)
