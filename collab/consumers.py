import logging
from asyncio import gather
from copy import deepcopy
from typing import Any, Dict, List, Sequence
import uuid

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now

from ltiapi.models import CustomUser

from . import models as m
from .utils import dump_content, user_id_for_room

logger = logging.getLogger("collab")


create_record = database_sync_to_async(m.ExcalidrawLogRecord.objects.create)
upsert_room = database_sync_to_async(m.ExcalidrawRoom.objects.update_or_create)
bulk_create_rcords = database_sync_to_async(m.ExcalidrawLogRecord.objects.bulk_create)


class CollaborationConsumer(AsyncJsonWebsocketConsumer):
    allowed_methods = {'collaborator_change', 'elements_changed', 'save_room', 'full_sync'}
    channel_prefix = 'draw_room_'

    @property
    def group_name(self):
        return self.channel_prefix + self.room_name

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        try:
            return await super().receive(text_data, bytes_data, **kwargs)
        except Exception as e:
            logger.error(e)
            raise e from e

    async def connect(self):
        url_route: dict = self.scope.get('url_route')
        # pylint: disable=attribute-defined-outside-init
        self.args: Sequence[Any] = url_route.get('args')
        self.kwargs: Dict[str, Any] = url_route.get('kwargs')

        self.user: CustomUser = self.scope.get('user')
        self.room_name = self.kwargs.get('room_name')

        self.user_room_id = self.user.id_for_room(self.room_name) \
            if self.user.id is not None \
            else user_id_for_room(uuid.uuid4(), self.room_name)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        return await super().connect()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        return await super().disconnect(code)

    async def receive_json(self, content, *args, **kwargs):
        msg_type = content['eventtype']
        # logger.debug('received json: %s in %s', content, self.__class__.__name__)
        if msg_type in self.allowed_methods:
            method = getattr(self, msg_type)
            return await method(**content, **self.kwargs)
        raise ValueError(f'The message type "{msg_type}" is not allowed.')

    async def send_event(self, eventtype, **kwargs):
        await self.channel_layer.group_send(
            self.group_name, {
                'eventtype': eventtype,
                **kwargs,
                'type': 'notify_client',
                'user_room_id': self.user_room_id})

    async def collaborator_change(self, eventtype, changes: List[dict], room_name, **kwargs):
        # logger.debug("called collaborator_change")
        collaborator_to_send = deepcopy(changes[-1])
        records = []
        for change in changes:
            del change['username']
            time = change.pop('time', None)
            time = parse_datetime(time) if time else now()
            record = m.ExcalidrawLogRecord(
                room_name=room_name,
                event_type=eventtype,
                user_pseudonym=self.user_room_id,
                created_at=time
            )
            record.content = change
            records.append(record)

        collaborator_to_send['userRoomId'] = self.user_room_id
        await gather(
            bulk_create_rcords(records),
            self.send_event(eventtype, changes=[collaborator_to_send]))

    async def full_sync(self, eventtype, elements, room_name, **kwargs):
        await gather(
            self.elements_changed(eventtype, elements, room_name, **kwargs),
            self.save_room(elements, room_name, **kwargs))

    async def elements_changed(self, eventtype, elements, room_name, **kwargs):
        record = m.ExcalidrawLogRecord(
            room_name=room_name,
            event_type=eventtype,
            user_pseudonym=self.user_room_id
        )
        record.content = elements
        await gather(
            database_sync_to_async(record.save)(),
            self.send_event(eventtype, elements=elements))

    async def save_room(self, elements, room_name, **kwargs):
        elements, _ = dump_content(elements)
        room, _ = await upsert_room(
            room_name=room_name,
            defaults={'_elements': elements})
        logger.debug("room %s saved", room.room_name)

    async def notify_client(self, event: dict):
        # logger.debug('notified with %s', event)
        # dont't send the event back to the sender
        if event.pop('user_room_id') != self.user_room_id:
            await self.send_json(event)


# TODO: ...
# - store the start appstate
# - store a current appstate
# - insert user id for room on collaborator change
