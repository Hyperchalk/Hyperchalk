import logging

from django.urls import path

from . import consumers

logger = logging.getLogger('collab')


app_name = "collab"

urlpatterns = [
    path('collaborate/<room_name>', consumers.CollaborationConsumer.as_asgi(), name='collaborate')
]
