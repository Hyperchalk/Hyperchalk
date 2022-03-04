import asyncio
import logging

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.conf import settings
from django.http import HttpRequest, HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from draw.utils import (absolute_reverse, make_room_name, require_login, require_staff_user,
                        user_is_authenticated, user_is_authorized)

from . import models as m

logger = logging.getLogger('draw.collab')

get_or_create_room = database_sync_to_async(m.ExcalidrawRoom.objects.get_or_create)
async_get_object_or_404 = sync_to_async(get_object_or_404)

@database_sync_to_async
def get_username(user):
    return (user.first_name or user.username) if user.pk else _("Anonymous")

NOT_LOGGED_IN = _("You need to be logged in.")

async def index(request: HttpRequest, *args, **kwargs):
    # See issue #8
    if settings.ALLOW_AUTOMATIC_ROOM_CREATION:
        room_uri = reverse('collab:room', kwargs={'room_name': make_room_name(24)})
        return redirect(request.build_absolute_uri(room_uri), permanent=False)
    return HttpResponseBadRequest(_('Automatic room creation is disabled here.'))

async def room(request: HttpRequest, room_name: str):
    room_tpl, username = await asyncio.gather(
        get_or_create_room(room_name=room_name),
        get_username(request.user))
    room_obj, __ = room_tpl

    if not settings.ALLOW_ANONYMOUS_VISITS:
        authenticated, authorized = await asyncio.gather(
            user_is_authenticated(request.user),
            user_is_authorized(request.user, room_obj))
        if not authenticated:
            logger.warning("Someone tried to access %s without being authenticated.", room_name)
            return HttpResponseForbidden(_("You need to be logged in."))
        if not authorized:
            logger.warning(
                "User %s tried to access %s but is not allowed to access it.",
                username, room_name)
            return HttpResponseForbidden(_("You are not allowed to access this room."))

    return render(request, 'collab/index.html', {
        'excalidraw_config': {
            'BROADCAST_RESOLUTION': settings.BROADCAST_RESOLUTION,
            'ELEMENT_UPDATES_BEFORE_FULL_RESYNC': 100,
            'LANGUAGE_CODE': settings.LANGUAGE_CODE,
            'LIBRARY_RETURN_URL': absolute_reverse(request, 'collab:add-library'),
            'ROOM_NAME': room_name,
            'SAVE_ROOM_MAX_WAIT': 15000,
            'SOCKET_URL': request.build_absolute_uri(f'/ws/collab/{room_name}/collaborate')\
                .replace('http://', 'ws://', 1)\
                .replace('https://', 'wss://', 1), # not beautiful but it works
            'USER_NAME': username,
        },
        'custom_messages': {
            'NOT_LOGGED_IN': NOT_LOGGED_IN
        },
        'initial_data': room_obj.elements,
    })


@require_login
async def get_current_elements(request: HttpRequest, room_name: str):
    room_obj, __ = await get_or_create_room(room_name=room_name)
    return JsonResponse({
        'elements': room_obj.elements
    })


@require_staff_user
async def get_log_record(request: HttpRequest, room_name: str, pk: int):
    log_obj = await async_get_object_or_404(m.ExcalidrawLogRecord, pk=pk)
    return JsonResponse(log_obj.content, safe=False)


@require_staff_user
async def replay(request: HttpRequest, room_name: str, **kwargs):
    return render(request, 'collab/index.html', {
        'excalidraw_config': {
            'BROADCAST_RESOLUTION': settings.BROADCAST_RESOLUTION,
            'ELEMENT_UPDATES_BEFORE_FULL_RESYNC': 100,
            'IS_REPLAY_MODE': True,
            'LANGUAGE_CODE': settings.LANGUAGE_CODE,
            'LIBRARY_RETURN_URL': absolute_reverse(request, 'collab:add-library'),
            'ROOM_NAME': room_name,
            'SAVE_ROOM_MAX_WAIT': settings.SAVE_ROOM_MAX_WAIT,
            'SOCKET_URL': request.build_absolute_uri(f'/ws/collab/{room_name}/replay')\
                .replace('http://', 'ws://', 1)\
                .replace('https://', 'wss://', 1), # not beautiful but it works
            'USER_NAME': '',
        },
        'custom_messages': {
            'NOT_LOGGED_IN': NOT_LOGGED_IN
        },
        'initial_data': []
    })
