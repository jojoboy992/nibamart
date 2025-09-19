import os
import django
from django.core.asgi import get_asgi_application

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'niba_mart_project.settings')

# Initialize Django BEFORE importing channels routing
django.setup()

# Now import channels components
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import niba_mart_app.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            niba_mart_app.routing.websocket_urlpatterns
        )
    ),
})