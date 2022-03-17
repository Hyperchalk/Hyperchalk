import asyncio
import logging
from typing import Literal, cast
from urllib.parse import urlunsplit

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from collab.types import ExcalidrawBinaryFile
from draw.utils import absolute_reverse, make_room_name, validate_room_name
from draw.utils.auth import (require_login, require_staff_user, user_is_authenticated,
                             user_is_authorized)

from . import models as m

logger = logging.getLogger('draw.collab')

get_or_create_room = database_sync_to_async(m.ExcalidrawRoom.objects.get_or_create)
async_get_object_or_404 = sync_to_async(get_object_or_404)


@database_sync_to_async
def get_username(user):
    return (user.first_name or user.username) if user.pk else _("Anonymous")


def reverse_ws_url(request: HttpRequest, route: Literal["replay", "collaborate"], room_name: str):
    return urlunsplit((
        'wss' if request.is_secure() else 'ws',
        request.get_host(),
        f'/ws/collab/{room_name}/{route}',
        None,
        None))

@database_sync_to_async
def get_file_dicts(room_obj: m.ExcalidrawRoom):
    return {f.element_file_id: f.to_excalidraw_file_dict() for f in room_obj.files.all()}

NOT_LOGGED_IN = _("You need to be logged in.")


async def access_check(request: HttpRequest, room_obj: m.ExcalidrawRoom):
    if not settings.ALLOW_ANONYMOUS_VISITS:
        authenticated, authorized = await asyncio.gather(
            user_is_authenticated(request.user),
            user_is_authorized(request.user, room_obj, request.session))
        if not authenticated:
            logger.warning(
                "Someone tried to access %s without being authenticated.",
                room_obj.room_name)
            raise PermissionDenied(_("You need to be logged in."))
        if not authorized:
            logger.warning(
                "User %s tried to access %s but is not allowed to access it.",
                await sync_to_async(lambda: request.user.username), # type: ignore
                room_obj.room_name)
            raise PermissionDenied(_("You are not allowed to access this room."))


async def index(request: HttpRequest, *args, **kwargs):
    # See issue #8
    if settings.ALLOW_AUTOMATIC_ROOM_CREATION:
        room_uri = reverse('collab:room', kwargs={'room_name': make_room_name(24)})
        return redirect(request.build_absolute_uri(room_uri), permanent=False)
    return HttpResponseBadRequest(_('Automatic room creation is disabled here.'))


async def room(request: HttpRequest, room_name: str):
    # FIXME: forbidden automatic room creation can be circumvented if someone makes up a valid id
    validate_room_name(room_name)
    room_tpl, username = await asyncio.gather(
        get_or_create_room(room_name=room_name),
        get_username(request.user))
    room_obj, __ = room_tpl

    await access_check(request, room_obj)

    return render(request, 'collab/index.html', {
        'excalidraw_config': {
            'BROADCAST_RESOLUTION': settings.BROADCAST_RESOLUTION,
            'ELEMENT_UPDATES_BEFORE_FULL_RESYNC': 100,
            'LANGUAGE_CODE': settings.LANGUAGE_CODE,
            'LIBRARY_RETURN_URL': absolute_reverse(request, 'collab:add-library'),
            'ROOM_NAME': room_name,
            'SAVE_ROOM_MAX_WAIT': 15000,
            'SOCKET_URL': reverse_ws_url(request, "collaborate", room_name),
            'USER_NAME': username,
        },
        'custom_messages': {
            'NOT_LOGGED_IN': NOT_LOGGED_IN
        },
        'initial_elements': room_obj.elements,
        'files': await get_file_dicts(room_obj)
    })


@require_staff_user
async def replay(request: HttpRequest, room_name: str, **kwargs):
    room_obj = await async_get_object_or_404(m.ExcalidrawRoom, room_name=room_name)
    return render(request, 'collab/index.html', {
        'excalidraw_config': {
            'BROADCAST_RESOLUTION': settings.BROADCAST_RESOLUTION,
            'ELEMENT_UPDATES_BEFORE_FULL_RESYNC': 100,
            'IS_REPLAY_MODE': True,
            'LANGUAGE_CODE': settings.LANGUAGE_CODE,
            'LIBRARY_RETURN_URL': absolute_reverse(request, 'collab:add-library'),
            'ROOM_NAME': room_name,
            'SAVE_ROOM_MAX_WAIT': settings.SAVE_ROOM_MAX_WAIT,
            'SOCKET_URL': reverse_ws_url(request, "replay", room_name),
            'USER_NAME': '',
        },
        'custom_messages': {
            'NOT_LOGGED_IN': NOT_LOGGED_IN
        },
        'initial_elements': [],
        'files': await get_file_dicts(room_obj)
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


@sync_to_async
def get_room_record_ids(room_name: str):
    return [rec_id for (rec_id,) in m.ExcalidrawLogRecord.objects\
        .filter(room_name=room_name)\
        .order_by('id')\
        .values_list('id')]


@require_staff_user
async def get_log_record_ids(request: HttpRequest, room_name: str, *args, **kwargs):
    return JsonResponse(await get_room_record_ids(room_name), safe=False)


@require_login
async def save_file(request: HttpRequest, room_name: str):
    """
    It is assumed that the client delivers the data as application/x-www-form-urlencoded.
    """
    room_obj, __ = get_or_create_room(room_name=room_name)
    await access_check(request, room_obj)
    f = m.ExcalidrawFile.from_excalidraw_file_dict(
        room_obj, cast(ExcalidrawBinaryFile, request.POST))
    await sync_to_async(f.save)()
    return HttpResponse()
