"""
ASGI config for CONTROL_TEMPERATURA project.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import DASHBOARD_TEMP_VOLT.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CONTROL_TEMPERATURA.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            DASHBOARD_TEMP_VOLT.routing.websocket_urlpatterns
        )
    ),
})
