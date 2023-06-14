import asyncio
import logging
from typing import Literal
from urllib.parse import urlunsplit

from channels.db import database_sync_to_async
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from draw.utils import absolute_reverse, make_room_name, reverse_with_query, validate_room_name
from draw.utils.auth import require_staff_user, user_is_authenticated, Unauthenticated, user_is_staff

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


@database_sync_to_async
def course_exists(room_obj: m.ExcalidrawRoom):
    return hasattr(room_obj, 'course')


def custom_messages():
    return {
        'NOT_LOGGED_IN': _("You need to be logged in."),
        'FILE_TOO_LARGE': _("The file you've added is too large."),
    }


async def index(request: HttpRequest, *args, **kwargs):
    if settings.SHOW_CREATE_ROOM_PAGE:
        # show the room creation page on GET
        if request.method == 'GET':
            return render(request, 'collab/index.html', {
                'imprint_url': settings.IMPRINT_URL,
            })

        # on POST, redirect to the room, after checking that it doesn't exist yet
        if (room_name := request.POST.get('roomname')):
            try:
                validate_room_name(room_name)
            except ValidationError:
                return render(request, 'collab/index.html', {
                    'imprint_url': settings.IMPRINT_URL,
                    'error_message': _(
                        '“%s” is not a valid room name. The room name must have between 10 and 24 characters. '
                        'The following characters are allowed: a-z, A-Z, 0-9, -, _'
                    ) % room_name })

            __, created = await get_or_create_room(room_name=room_name)
            if created:
                return redirect(absolute_reverse(request, 'collab:room', kwargs={'room_name': room_name}))
            else:
                return render(request, 'collab/index.html', {
                    'imprint_url': settings.IMPRINT_URL,
                    'error_message': _('The room name “%(room_name)s” is already taken.') % {'room_name': room_name}})

    # create a random room name if none is given
    if settings.ALLOW_AUTOMATIC_ROOM_CREATION:
        if settings.ALLOW_ANONYMOUS_VISITS or await user_is_authenticated(request.user):
            room_name = make_room_name(24)
            __, created = await get_or_create_room(room_name=room_name)
            if not created:
                # retry in the unlikely case that the room name is already taken
                return redirect(absolute_reverse(request, 'collab:index'))
            room_uri = reverse('collab:room', kwargs={'room_name': room_name})
            return redirect(request.build_absolute_uri(room_uri), permanent=False)
        else:
            return redirect(
                reverse_with_query('admin:login', query_kwargs={'next': f'/{make_room_name(24)}/'}))

    else:
        return HttpResponseBadRequest(_('Automatic room creation is disabled here.'))


async def room(request: HttpRequest, room_name: str):
    validate_room_name(room_name)
    room_obj, username = await asyncio.gather(
        async_get_object_or_404(m.ExcalidrawRoom, room_name=room_name),
        get_username(request.user))

    try:
        await room_access_check(request, room_obj)
    except Unauthenticated:
        return redirect(reverse_with_query('admin:login', query_kwargs={'next': request.path}))

    is_lti_room, is_staff, file_dicts = await asyncio.gather(
        course_exists(room_obj),
        user_is_staff(request.user),
        get_file_dicts(room_obj))

    return render(request, 'collab/room.html', {
        'excalidraw_config': {
            'FILE_URL_TEMPLATE': absolute_reverse(request, 'api-1:put_file', kwargs={
                'room_name': room_name, 'file_id': 'FILE_ID'}),
            'BROADCAST_RESOLUTION_THROTTLE_MSEC': settings.BROADCAST_RESOLUTION_THROTTLE_MSEC,
            'ELEMENT_UPDATES_BEFORE_FULL_RESYNC': 100,
            'LANGUAGE_CODE': settings.LANGUAGE_CODE,
            'LIBRARY_RETURN_URL': absolute_reverse(request, 'collab:add-library'),
            'ROOM_NAME': room_name,
            'SAVE_ROOM_MAX_WAIT_MSEC': settings.SAVE_ROOM_MAX_WAIT_MSEC,
            'SHOW_QR_CODE': not is_lti_room,
            'SOCKET_URL': reverse_ws_url(request, "collaborate", room_name),
            'USER_NAME': username,
            'USER_IS_STAFF': is_staff,
        },
        'custom_messages': custom_messages(),
        'initial_elements': room_obj.elements,
        'files': file_dicts,
        'room': room_obj,
        'show_privacy_notice': not is_lti_room and room_obj.tracking_enabled
    })


@require_staff_user()
async def replay(request: HttpRequest, room_name: str, **kwargs):
    room_obj = await async_get_object_or_404(m.ExcalidrawRoom, room_name=room_name)
    return render(request, 'collab/room.html', {
        'excalidraw_config': {
            'FILE_URL_TEMPLATE': absolute_reverse(request, 'api-1:put_file', kwargs={
                'room_name': room_name, 'file_id': '{file_id}'}),
            'IS_REPLAY_MODE': True,
            'LANGUAGE_CODE': settings.LANGUAGE_CODE,
            'LIBRARY_RETURN_URL': absolute_reverse(request, 'collab:add-library'),
            'ROOM_NAME': room_name,
            'SOCKET_URL': reverse_ws_url(request, "replay", room_name),
        },
        'custom_messages': custom_messages(),
        'initial_elements': [],
        'files': await get_file_dicts(room_obj)
    })
