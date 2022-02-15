"""
ASGI config for draw project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path
from django.conf import settings
from .urlconf import ws_include
from .utils import apply_middleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'draw.settings')

http_application = get_asgi_application()

# def apply_middleware_from_settings()

application = ProtocolTypeRouter({
    "http": http_application,
    "websocket": apply_middleware(
        *settings.WS_MIDDLEWARE,
        URLRouter([ path('ws/', ws_include('draw.urls_ws')) ]),
    ),
    # "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter())),
})
