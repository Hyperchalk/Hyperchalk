import asyncio
import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from draw.utils.auth import user_is_authenticated, user_is_authorized

from . import models as m

logger = logging.getLogger('draw.collab')

get_or_create_room = sync_to_async(m.ExcalidrawRoom.objects.get_or_create)

async_get_object_or_404 = sync_to_async(get_object_or_404)

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

@sync_to_async
def get_room_record_ids(room_name: str):
    return [rec_id for (rec_id,) in m.ExcalidrawLogRecord.objects\
        .filter(room_name=room_name)\
        .order_by('id')\
        .values_list('id')]
