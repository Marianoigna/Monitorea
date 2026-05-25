import json
from channels.generic.websocket import AsyncWebsocketConsumer


class TemperaturaConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        """Cliente se conecta → entra al grupo 'temperatura'."""
        await self.channel_layer.group_add('temperatura', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        """Cliente se desconecta → sale del grupo."""
        await self.channel_layer.group_discard('temperatura', self.channel_name)

    async def send_temperatura(self, event):
        """Recibe el evento del grupo y lo envía al cliente WebSocket."""
        await self.send(text_data=json.dumps({
            'sensor_id': event['sensor_id'],
            'valor': event['valor'],
            'timestamp': event['timestamp'],
        }))
