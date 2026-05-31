from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/telemetria/(?P<mac>[A-Fa-f0-9:]+)/$', consumers.TelemetriaConsumer.as_asgi()),
]
