"""
ASGI config for draw project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter #, URLRouter
from django.core.asgi import get_asgi_application

http_application = get_asgi_application()

# disable pylint because the application needs to be initialised before these imports
# pylint: disable=wrong-import-order,ungrouped-imports,wrong-import-position
# import collab.routing
# from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'draw.settings')

application = ProtocolTypeRouter({
    "http": http_application,
    # "websocket": AuthMiddlewareStack(URLRouter(
    #     collab.routing.websocket_urlpatterns,
    # )),
})
