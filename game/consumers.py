import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CasinoFloorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'global_casino_floor'
        self.user = self.scope.get('user')

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        if self.user and self.user.is_authenticated:
            self.user_group_name = f'user_{self.user.id}'
            await self.channel_layer.group_add(self.user_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def gjp_update(self, event):
        await self.send(text_data=json.dumps({'type': 'gjp_update', 'island_id': event['island_id'], 'new_value': event['new_value']}))

    async def global_jackpot_hit(self, event):
        await self.send(text_data=json.dumps({'type': 'jackpot_hit', 'island_id': event['island_id'], 'island_name': event['island_name'], 'winner_name': event['winner_name'], 'amount': event['amount']}))

    async def personal_notification(self, event):
        await self.send(text_data=json.dumps({'type': 'personal_notification', 'title': event['title'], 'message': event['message'], 'new_balance': event.get('new_balance')}))

    # NEW: Machine Live Occupancy Sync
    async def machine_update(self, event):
        await self.send(text_data=json.dumps({'type': 'machine_update', 'machine_id': event['machine_id'], 'is_occupied': event['is_occupied']}))