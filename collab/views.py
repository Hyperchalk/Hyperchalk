

from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from channels.db import database_sync_to_async
from draw.utils import reverse_with_query

from .utils import make_room_name
from . import models as m

get_room_elements = database_sync_to_async(m.ExcalidrawRoom.objects.get_or_create)

async def index(request: HttpRequest, **kwargs):
    room = request.GET.get('room', None)
    if not room:
        room_uri = reverse_with_query('collab:index', query_kwargs={'room': make_room_name(24)})
        return redirect(request.build_absolute_uri(room_uri), permanent=False)

    room_obj, _ = await get_room_elements(room_name=room)
    return render(request, 'collab/index.html', {'excalidraw_config': {
        'SOCKET_URL': request.build_absolute_uri('/ws/collab/collaborate/' + room)\
            .replace('http://', 'ws://', 1),
        'BROADCAST_RESOLUTION': 200,
        'ROOM_NAME': room,
        'INITIAL_DATA': room_obj.elements
    }})

async def get_current_elements(request: HttpRequest, room_name: str):
    room_obj, _ = await get_room_elements(room_name=room_name)
    return JsonResponse({
        'elements': room_obj.elements
    })
