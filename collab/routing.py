import logging

from django.urls import path
from django.urls.base import get_script_prefix

from . import consumers

logger = logging.getLogger('collab')

prefix = get_script_prefix().strip('/')
ws_url = prefix + '/' if prefix else '' + 'ws/'
# TODO: script prefix does not work yet. this has been solved using nginx config.

websocket_urlpatterns = [
    path(ws_url + 'signaling/',
         consumers.SignalingConsumer.as_asgi(), name="signaling"),
    path(ws_url + 'persisting/',
         consumers.CrdtPersistanceConsumer.as_asgi(), name="persisting"),
]
