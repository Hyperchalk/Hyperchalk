import logging

from django.urls import path

from . import consumers

logger = logging.getLogger('draw.collab')


app_name = "collab"

urlpatterns = [
    path('<room_name>/collaborate', consumers.CollaborationConsumer.as_asgi(), name='collaborate'),
    path('<room_name>/replay', consumers.ReplayConsumer.as_asgi(), name='replay')
]
