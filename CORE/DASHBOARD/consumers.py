import json
from channels.generic.websocket import AsyncWebsocketConsumer


class TelemetriaConsumer(AsyncWebsocketConsumer):
    """WebSocket por dispositivo (MAC). Grupo: telemetria_<MAC_con_guiones>."""

    async def connect(self):
        mac = self.scope['url_route']['kwargs']['mac'].upper()
        self.group_name = f'telemetria_{mac.replace(":", "_")}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_telemetria(self, event):
        await self.send(text_data=json.dumps({
            'mac': event['mac'],
            't': event['t'],
            'v': event['v'],
        }))
