import asyncio
import logging
from typing import Literal
from urllib.parse import urlunsplit

from channels.db import database_sync_to_async
from django.conf import settings
from django.http import HttpRequest, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from draw.utils import absolute_reverse, make_room_name, validate_room_name
from draw.utils.auth import require_staff_user

from . import models as m
from .utils import room_access_check, async_get_object_or_404, get_or_create_room

logger = logging.getLogger('draw.collab')


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
    return {f.element_file_id: f.to_excalidraw_file_schema().dict() for f in room_obj.files.all()}

NOT_LOGGED_IN = _("You need to be logged in.")


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

    await room_access_check(request, room_obj)

    return render(request, 'collab/index.html', {
        'excalidraw_config': {
            'FILE_URL_TEMPLATE': absolute_reverse(request, 'api-1:put_file', kwargs={
                'room_name': room_name, 'file_id': 'FILE_ID'}),
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


@require_staff_user()
async def replay(request: HttpRequest, room_name: str, **kwargs):
    room_obj = await async_get_object_or_404(m.ExcalidrawRoom, room_name=room_name)
    return render(request, 'collab/index.html', {
        'excalidraw_config': {
            'FILE_URL_TEMPLATE': absolute_reverse(request, 'api-1:put_file', kwargs={
                'room_name': room_name, 'file_id': '{file_id}'}),
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
