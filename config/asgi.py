"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

# 1. Initialize Django settings FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 2. Boot the core Django app early. This prevents the settings crash.
django_asgi_app = get_asgi_application()

# 3. NOW it is safe to import WebSockets, routing, and database models
from channels.routing import ProtocolTypeRouter, URLRouter
from game.routing import websocket_urlpatterns
from users.middleware import JWTAuthMiddlewareStack

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})