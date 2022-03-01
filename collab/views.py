import asyncio
import logging

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.conf import settings
from django.http import HttpRequest, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as txt

from draw.utils import (make_room_name, require_login, require_staff_user, reverse_with_query,
                        user_is_authenticated, user_is_authorized)

from . import models as m

logger = logging.getLogger('draw.collab')

get_or_create_room = database_sync_to_async(m.ExcalidrawRoom.objects.get_or_create)
async_get_object_or_404 = sync_to_async(get_object_or_404)

@database_sync_to_async
def get_username(user):
    return (user.first_name or user.username) if user.pk else txt("Anonymous")

NOT_LOGGED_IN = txt("You need to be logged in.")


async def index(request: HttpRequest, **kwargs):
    room_name = request.GET.get('room', None)
    if not room_name:
        # See issue #8
        if settings.ALLOW_AUTOMATIC_ROOM_CREATION:
            room_uri = reverse_with_query('collab:index', query_kwargs={'room': make_room_name(24)})
            return redirect(request.build_absolute_uri(room_uri), permanent=False)
        return HttpResponseBadRequest(txt('No room parameter has been provided in the URL.'))

    room, username = await asyncio.gather(
        get_or_create_room(room_name=room_name),
        get_username(request.user))
    room_obj, _ = room

    if not settings.ALLOW_ANONYMOUS_VISITS:
        authenticated, authorized = await asyncio.gather(
            user_is_authenticated(request.user),
            user_is_authorized(request.user, room_obj))
        if not authenticated:
            logger.warning("Someone tried to access %s without being authenticated.", room_name)
            return HttpResponseForbidden(txt("You need to be logged in."))
        if not authorized:
            logger.warning(
                "User %s tried to access %s but is not allowed to access it.",
                username, room_name)
            return HttpResponseForbidden(txt("You are not allowed to access this room."))

    return render(request, 'collab/index.html', {'excalidraw_config': {
        'SOCKET_URL': request.build_absolute_uri('/ws/collab/collaborate/' + room_name)\
            .replace('http://', 'ws://', 1)\
            .replace('https://', 'wss://', 1), # not beautiful but it works
        'BROADCAST_RESOLUTION': 100,
        'ROOM_NAME': room_name,
        'INITIAL_DATA': room_obj.elements,
        'USER_NAME': username,
        'LANGUAGE_CODE': settings.LANGUAGE_CODE,
        'ELEMENT_UPDATES_BEFORE_FULL_RESYNC': 100,
        'SAVE_ROOM_INTERVAL': 15000
    },
    'custom_messages': {
        'NOT_LOGGED_IN': NOT_LOGGED_IN
    }})


@require_login
async def get_current_elements(request: HttpRequest, room_name: str):
    room_obj, _ = await get_or_create_room(room_name=room_name)
    return JsonResponse({
        'elements': room_obj.elements
    })


@require_staff_user
async def get_log_record(request: HttpRequest, pk: int):
    log_obj = await async_get_object_or_404(m.ExcalidrawLogRecord, pk=pk)
    return JsonResponse(log_obj.content, safe=False)
