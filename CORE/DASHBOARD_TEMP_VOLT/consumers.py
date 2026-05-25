import json
from channels.generic.websocket import AsyncWebsocketConsumer


class TemperaturaConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.channel_layer.group_add('temperatura', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('temperatura', self.channel_name)

    async def send_temperatura(self, event):
        await self.send(text_data=json.dumps({
            'sensor_id': event['sensor_id'],
            'valor': event['valor'],
            'timestamp': event['timestamp'],
        }))


class VoltajeConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        await self.channel_layer.group_add('voltaje', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('voltaje', self.channel_name)

    async def send_voltaje(self, event):
        await self.send(text_data=json.dumps({
            'sensor_id': event['sensor_id'],
            'valor': event['valor'],
            'timestamp': event['timestamp'],
        }))
