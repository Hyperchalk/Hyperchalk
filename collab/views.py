from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from draw.utils import make_room_name, require_login, require_staff_user, reverse_with_query

from . import models as m

get_room_elements = database_sync_to_async(m.ExcalidrawRoom.objects.get_or_create)
async_get_object_or_404 = sync_to_async(get_object_or_404)

@database_sync_to_async
def get_username(user):
    return (user.first_name or user.username) if user.pk else _("Anonymous")

async def index(request: HttpRequest, **kwargs):
    """
    The index view will generate a new room if
    """
    room = request.GET.get('room', None)
    if not room:
        room_uri = reverse_with_query('collab:index', query_kwargs={'room': make_room_name(24)})
        return redirect(request.build_absolute_uri(room_uri), permanent=False)

    room_obj, _ = await get_room_elements(room_name=room)
    return render(request, 'collab/index.html', {'excalidraw_config': {
        'SOCKET_URL': request.build_absolute_uri('/ws/collab/collaborate/' + room)\
            .replace('http://', 'ws://', 1)\
            .replace('https://', 'wss://', 1),
        'BROADCAST_RESOLUTION': 100,
        'ROOM_NAME': room,
        'INITIAL_DATA': room_obj.elements,
        'USER_NAME': await get_username(request.user),
        'LANGUAGE_CODE': settings.LANGUAGE_CODE,
        'ELEMENT_UPDATES_BEFORE_FULL_RESYNC': 100,
        'SAVE_ROOM_INTERVAL': 15000
    }})


@require_login
async def get_current_elements(request: HttpRequest, room_name: str):
    room_obj, _ = await get_room_elements(room_name=room_name)
    return JsonResponse({
        'elements': room_obj.elements
    })


@require_staff_user
async def get_log_record(request: HttpRequest, pk: int):
    log_obj = await async_get_object_or_404(m.ExcalidrawLogRecord, pk=pk)
    return JsonResponse(log_obj.content, safe=False)
