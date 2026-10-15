"""
Configuración ASGI para el proyecto Poki Koa.
Punto de entrada para servidores web asíncronos (Daphne).
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from cunas.routing import websocket_urlpatterns

# Establecer variable de entorno para la configuración de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "poki_koa.settings")

# Inicializa la aplicación ASGI nativa de Django para manejar peticiones HTTP regulares
django_asgi_app = get_asgi_application()

# ProtocolTypeRouter redirige el tráfico dependiendo del protocolo:
# HTTP -> Django clásico
# WebSocket -> Channels
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})