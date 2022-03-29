from asyncio import gather

from asgiref.sync import sync_to_async
from django.db.utils import IntegrityError
from django.http import HttpRequest
from ninja import Router

from draw.utils.auth import request_user_is_staff

from . import models as m
from .types import ExcalidrawBinaryFile
from .utils import access_check, async_get_object_or_404, get_or_create_room, get_room_record_ids

collab_router = Router(tags=['collab'])


@collab_router.get(
    '/room/{room_name}/file/{file_id}.json',
    response=ExcalidrawBinaryFile, url_name="get_file")
async def get_file(request: HttpRequest, room_name: str, file_id: str):
    room_tuple, file_obj = await gather(
        get_or_create_room(room_name=room_name),
        async_get_object_or_404(m.ExcalidrawFile, element_file_id=file_id, belongs_to=room_name))
    room_obj, __ = room_tuple
    await access_check(request, room_obj)
    return file_obj.to_excalidraw_file_schema()


@collab_router.put('/room/{room_name}/file/{file_id}.json', url_name="put_file")
async def put_file(request: HttpRequest, room_name: str, file_id: str,
                   content: ExcalidrawBinaryFile):
    room_obj, __ = await get_or_create_room(room_name=room_name)
    await access_check(request, room_obj)
    file_obj = m.ExcalidrawFile.from_excalidraw_file_schema(room_name, content)
    try:
        await sync_to_async(file_obj.save)()
    except IntegrityError:
        # the file is already there. just act like everything was ok.
        pass
    return {'id': file_id}


@collab_router.get('/{room_name}/index.json', auth=[request_user_is_staff], url_name="get_room")
async def get_room(request: HttpRequest, room_name: str):
    room_obj, __ = await get_or_create_room(room_name=room_name)
    return room_obj.elements


@collab_router.get(
    '/{room_name}/records.json',
    auth=[request_user_is_staff], url_name="get_record_ids")
async def get_record_ids(request: HttpRequest, room_name: str):
    return await get_room_record_ids(room_name)


@collab_router.get(
    '/{room_name}/records/{pk}.json',
    auth=[request_user_is_staff], url_name="get_record")
async def get_record(request: HttpRequest, room_name: str, pk: int):
    log_obj = await async_get_object_or_404(m.ExcalidrawLogRecord, pk=pk)
    return log_obj.content
