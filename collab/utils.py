import asyncio
import logging
from functools import wraps
from typing import Callable

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext_lazy as _

from draw.utils.auth import (Unauthenticated, Unauthorized, create_html_response_forbidden,
                             create_json_response_forbidden, user_is_authenticated,
                             user_is_authorized)

from . import models as m

logger = logging.getLogger('draw.collab')

get_or_create_room = sync_to_async(m.ExcalidrawRoom.objects.get_or_create)

room_name = sync_to_async(lambda r: r.room_name)

async def room_access_check(request: HttpRequest, room_obj: m.ExcalidrawRoom):
    """
    Checks if the logged in user has access to the supplied room object.

    :param request: the current request
    :type request: HttpRequest
    :param room_obj: the room to check the access for
    :type room_obj: m.ExcalidrawRoom
    :raises PermissionDenied: if the user is not authenticated or authorized to access the room
    """
    if await room_name(room_obj) in settings.PUBLIC_ROOMS:
        pass
    elif not settings.ALLOW_ANONYMOUS_VISITS:
        authenticated, authorized = await asyncio.gather(
            user_is_authenticated(request.user),
            user_is_authorized(request.user, room_obj, request.session))
        if not authenticated:
            logger.warning(
                "Someone tried to access %s without being authenticated.",
                room_obj.room_name)
            raise Unauthenticated(_("You need to be logged in."))
        if not authorized:
            logger.warning(
                "User %s tried to access %s but is not allowed to access it.",
                await sync_to_async(lambda: request.user.username)(), # type: ignore
                room_obj.room_name)
            raise Unauthorized(_("You are not allowed to access this room."))

def require_room_access(json=False):
    """
    Creates an async decorator for testing if the current user has access to the room.

    Decorator is to be applied to view functions. Works
    with both django views and django ninja routes.

    :param json: whether to return a ``JsonResponse``, defaults to False
    :type json: bool, optional
    """
    create_response = create_json_response_forbidden if json else create_html_response_forbidden

    def decorator(async_func: Callable[..., HttpResponse]):
        @wraps(async_func)
        async def inner(request: HttpRequest, *args, room_name, **kwargs):
            try:
                room_obj, __ = await get_or_create_room(room_name=room_name)
                await room_access_check(request, room_obj)
                return await async_func(request, *args, room_name=room_name, **kwargs)
            except PermissionDenied as e:
                return create_response(e)
        return inner
    return decorator

@sync_to_async
def get_room_record_ids(room_name: str):
    return [rec_id for (rec_id,) in m.ExcalidrawLogRecord.objects\
        .filter(room_name=room_name)\
        .order_by('id')\
        .values_list('id')]
