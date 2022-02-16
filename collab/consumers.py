import logging
from asyncio import ensure_future
from typing import Any, Dict, Sequence

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AbstractBaseUser

from . import models as m
from .utils import dump_content

logger = logging.getLogger("collab")


class CollaborationConsumer(AsyncJsonWebsocketConsumer):
    allowed_methods = {'pointer_movement', 'elements_changed', 'save_room'}

    async def connect(self):
        url_route: dict = self.scope.get('url_route')
        # pylint: disable=attribute-defined-outside-init
        self.args: Sequence[Any] = url_route.get('args')
        self.kwargs: Dict[str, Any] = url_route.get('kwargs')
        self.user: AbstractBaseUser = self.scope.get('user')
        return await super().connect()

    async def receive_json(self, content, *args, **kwargs):
        msg_type = content['eventtype']
        # logger.debug(f'received json: {json_data} in {self.__class__.__name__}')
        if msg_type in self.allowed_methods:
            method = getattr(self, msg_type)
            return await method(**content, **self.kwargs)
        raise ValueError(f'The message type "{msg_type}" is not allowed.')

    async def pointer_movement(self, eventtype, pointer, room_name, **kwargs):
        ensure_future(self.store_record(
            room_name=room_name,
            content=pointer,
            event_type=eventtype,
            user=self.user.pk
        ))

    async def elements_changed(self, eventtype, elements, room_name, **kwargs):
        # ensure_future(self.save_room(elements, room_name))
        ensure_future(self.store_record(
            room_name=room_name,
            content=elements,
            event_type=eventtype,
            user=self.user.pk
        ))

    async def store_record(self, **kwargs):
        """
        Stores a record to the db.

        This is outsourced to a function so it can be triggered without waiting for the result.

        :param **kwargs: the kwargs will be passed to the ``ExcalidrawLogRecord`` constructor.
        """
        create_record = database_sync_to_async(m.ExcalidrawLogRecord.objects.create)
        record: m.ExcalidrawLogRecord = await create_record(**kwargs)
        logger.debug("recorded %s for room %s", record.event_type, record.room_name)


    async def save_room(self, elements, room_name, **kwargs):
        upsert_room = database_sync_to_async(m.ExcalidrawRoom.objects.update_or_create)
        room, _ = await upsert_room(
            room_name=room_name,
            defaults={'_elements': dump_content(elements)})
        logger.debug("room %s saved", room.room_name)

# TODO: ...
# - store the start appstate
# - store a current appstate
# - calculate the updates between the last appstate and the current appstate
# - store only first appstate, update diffs and current appstate to the db
