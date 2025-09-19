from django.urls import path
from .consumers import ChatConsumer
from . import consumers

websocket_urlpatterns = [
    path("ws/chat/<str:username>/", ChatConsumer.as_asgi()),
    path('ws/status/', consumers.StatusConsumer.as_asgi()),
    path("ws/notifications/", consumers.NotificationsConsumer.as_asgi()), 
]
