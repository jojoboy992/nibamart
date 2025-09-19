import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.other_username = self.scope['url_route']['kwargs']['username']
        self.user = self.scope['user']
        self.room_name = "_".join(sorted([self.user.username, self.other_username]))
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']

        # ✅ Save message only once
        message_id = await self.save_message(
            self.user.username, self.other_username, message
        )

        # ✅ Broadcast to chat room (sender + recipient will both see instantly)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "id": message_id,
                "message": message,
                "sender": self.user.username,
            }
        )

        # ✅ Send notification update to recipient
        recipient_unread_total = await self.get_unread_count(self.other_username)
        recipient_sender_unread = await self.get_sender_unread_count(
            self.user.username, self.other_username
        )

        await self.channel_layer.group_send(
            f"notifications_{self.other_username}",
            {
                "type": "new_message",
                "unread_count": recipient_unread_total,      # total for bell
                "sender": self.user.username,                # who sent it
                "sender_unread_count": recipient_sender_unread,  # per-sender count
            }
        )

    async def chat_message(self, event):
        """Send chat messages to WebSocket"""
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "id": event["id"],
            "message": event["message"],
            "sender": event["sender"],
        }))

    async def delete_message_event(self, event):
        """Broadcast a message deletion to all room members"""
        await self.send(text_data=json.dumps({
            "type": "delete_message",
            "message_id": event["message_id"],
        }))

    # ----------------------
    # Helpers
    # ----------------------
    @database_sync_to_async
    def save_message(self, sender_username, recipient_username, content):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        sender = User.objects.get(username=sender_username)
        recipient = User.objects.get(username=recipient_username)
        msg = Message.objects.create(
            sender=sender,
            recipient=recipient,
            content=content
        )
        return msg.id  # ✅ return ID

    @database_sync_to_async
    def get_unread_count(self, username):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(username=username)
        return Message.objects.filter(
            recipient=user, is_read=False
        ).count()

    @database_sync_to_async
    def get_sender_unread_count(self, sender_username, recipient_username):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        sender = User.objects.get(username=sender_username)
        recipient = User.objects.get(username=recipient_username)
        return Message.objects.filter(
            sender=sender, recipient=recipient, is_read=False
        ).count()

class StatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join status updates group
        await self.channel_layer.group_add(
            "status_updates",
            self.channel_name
        )
        await self.accept()
        
        # Set user online when they connect
        if self.scope['user'].is_authenticated:
            await self.set_user_online()

    async def disconnect(self, close_code):
        # Leave status updates group
        await self.channel_layer.group_discard(
            "status_updates", 
            self.channel_name
        )
        
        # Set user offline when they disconnect
        if self.scope['user'].is_authenticated:
            await self.set_user_offline()

    async def status_broadcast(self, event):
        # Send status update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'username': event['username'],
            'status': event['status'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def set_user_online(self):
        from .models import UserStatus
        user_status, created = UserStatus.objects.get_or_create(user=self.scope['user'])
        user_status.status = 'online'
        user_status.last_seen = timezone.now()
        user_status.save()

    @database_sync_to_async  
    def set_user_offline(self):
        from .models import UserStatus
        try:
            user_status = UserStatus.objects.get(user=self.scope['user'])
            user_status.status = 'offline'
            user_status.last_seen = timezone.now()
            user_status.save()
        except UserStatus.DoesNotExist:
            pass  


class NotificationsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_authenticated:
            self.user = self.scope["user"]
            self.group_name = f"notifications_{self.user.username}"

            # ✅ Join this user's notification group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    # ✅ FIXED: Forward ALL the data from ChatConsumer
    async def new_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "new_message",
            "unread_count": event["unread_count"],
            "sender": event.get("sender"),  # ✅ Forward sender
            "sender_unread_count": event.get("sender_unread_count"),  # ✅ Forward per-sender count
        }))

    # Optional helper (if needed in future)
    @database_sync_to_async
    def get_unread_count(self, user):
        return Message.objects.filter(recipient=user, is_read=False).count()