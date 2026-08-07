from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db.models import Q
from core.models import Chat

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        print(self.scope)
        if not user.is_authenticated:
            await self.close()
            return

        self.chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        self.group_chat = f"chat_{self.chat_id}"

        allowed = await self._is_chat_member(user.id, self.chat_id)
        if not allowed:
            await self.close()
            return


    @database_sync_to_async
    def _is_chat_member(self, user_id, chat_id):
        return (
            Chat.objects.filter(id=chat_id)
            .filter(Q(user1_id=user_id) | Q(user2_id=user_id))
            .exists()
        )

