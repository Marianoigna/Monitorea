"""
ASGI config for MONITOREA project.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import DASHBOARD_SENSORES.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MONITOREA.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            DASHBOARD_SENSORES.routing.websocket_urlpatterns
        )
    ),
})
