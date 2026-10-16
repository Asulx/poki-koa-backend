import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CotConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.grupo_cunas = 'monitoreo_cunas'

        await self.channel_layer.group_add(
            self.grupo_cunas,
            self.channel_name
        )
        await self.accept()
        print("Frontend conectado al WebSocket de Cunas exitosamente.")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.grupo_cunas,
            self.channel_name
        )
        print("Frontend desconectado del WebSocket.")

    async def cot_update(self, event):
        datos_cuna = event['message']
        await self.send(text_data=json.dumps({
            'type': 'actualizacion_cuna',
            'data': datos_cuna
        }))