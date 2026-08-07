import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Chat, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        self.friend_id = int(self.scope["url_route"]["kwargs"]["friend_id"])
        
        self.room_name = f"chat_{min(self.user.id, self.friend_id)}_{max(self.user.id, self.friend_id)}"
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
        except json.JSONDecodeError:
            return
            
        message_text = text_data_json.get("message", "").strip()
        target = text_data_json.get("target", "chat")

        if message_text:
            saved_messages = await self.save_message(message_text, target)
            
            for msg_data in saved_messages:
                recipient_id = msg_data["recipient_id"]
                room_name = f"chat_{min(self.user.id, recipient_id)}_{max(self.user.id, recipient_id)}"
                group_name = f"chat_{room_name}"
                
                await self.channel_layer.group_send(
                    group_name,
                    {
                        "type": "chat_message",
                        "message": msg_data
                    }
                )

                # Broadcast real-time notification to the recipient on the home list page
                recipient_notification_group = f"user_{recipient_id}_notifications"
                await self.channel_layer.group_send(
                    recipient_notification_group,
                    {
                        "type": "send_notification",
                        "notification": {
                            "sender_id": self.user.id,
                            "sender_username": self.user.username,
                            "type": "text",
                            "text": "New Message",
                            "created_at": "Just now",
                        }
                    }
                )

    @database_sync_to_async
    def save_message(self, message_text, target):
        from .views import get_message_recipients, get_or_create_chat
        
        User = get_user_model()
        try:
            friend = User.objects.get(pk=self.friend_id)
        except User.DoesNotExist:
            return []

        recipients = get_message_recipients(self.user, friend, target)
        saved_messages = []
        for recipient in recipients:
            chat = get_or_create_chat(self.user, recipient)
            msg = Message.objects.create(
                chat=chat,
                sender=self.user,
                reciever=recipient,
                text=message_text,
            )
            # Update last message time
            from django.utils import timezone
            chat.last_message = timezone.now()
            chat.save()

            saved_messages.append({
                "id": msg.id,
                "sender_id": self.user.id,
                "sender_username": self.user.username,
                "recipient_id": recipient.id,
                "text": msg.text,
                "image_url": None,
                "created_at": "Just now",
            })
        return saved_messages

    async def chat_message(self, event):
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "message": message
        }))


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        self.room_group_name = f"user_{self.user.id}_notifications"

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from room group
    async def send_notification(self, event):
        notification = event["notification"]

        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            "notification": notification
        }))
