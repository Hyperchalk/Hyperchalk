import logging
import traceback
import uuid
from asyncio import gather
from copy import deepcopy
from typing import Any, Dict, List, Sequence

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now

from ltiapi.models import CustomUser

from . import models as m
from .utils import dump_content, user_id_for_room

logger = logging.getLogger("collab")


create_record = database_sync_to_async(m.ExcalidrawLogRecord.objects.create)
bulk_create_records = database_sync_to_async(m.ExcalidrawLogRecord.objects.bulk_create)
upsert_room = database_sync_to_async(m.ExcalidrawRoom.objects.update_or_create)
get_or_create_room = database_sync_to_async(m.ExcalidrawRoom.objects.get_or_create)


class CollaborationConsumer(AsyncJsonWebsocketConsumer):
    allowed_eventtypes = {'collaborator_change', 'elements_changed', 'save_room', 'full_sync'}
    channel_prefix = 'draw_room_'

    @property
    def group_name(self):
        return self.channel_prefix + self.room_name

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        """
        Catch and log exceptions to the console as this is no default in django channels.
        """
        try:
            return await super().receive(text_data, bytes_data, **kwargs)
        except Exception as e:
            estring = "\n".join(traceback.format_exception(e))
            logger.error("\033[0;31m%s\033[0m", estring)
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
        """
        Notify all collaborators if a client left, so they
        can remove it from their collaborator list, too.
        """
        await self.send_event(
            eventtype='collaborator_left',
            collaborator={'userRoomId': self.user_room_id}
        )
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        return await super().disconnect(code)

    async def receive_json(self, content, *args, **kwargs):
        """
        When a JSON message is received, this calls the method
        which matches the ``eventtype`` field of that message.

        The method in ``eventtype`` must be in the set of
        ``allowed_eventtypes`` specified on the consumer.
        """
        msg_type = content['eventtype']
        # logger.debug('received json: %s in %s', content, self.__class__.__name__)
        if msg_type in self.allowed_eventtypes:
            method = getattr(self, msg_type)
            return await method(**content, **kwargs, **self.kwargs)
        raise ValueError(f'The eventtype "{msg_type}" is not allowed.')

    async def collaborator_change(self, room_name, eventtype, changes: List[dict], **kwargs):
        """
        Forwards all updates to users and their pointers to clients and logs them to the data base.
        """
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
            bulk_create_records(records),
            self.send_event(eventtype, changes=[collaborator_to_send]))

    async def full_sync(self, room_name, eventtype, elements, **kwargs):
        """
        Forwards all full syncs to clients, logs them to the data base and saves the room.
        """
        await gather(
            self.elements_changed(room_name, eventtype, elements=elements, **kwargs),
            self.save_room(room_name, elements, **kwargs))

    async def elements_changed(self, room_name, eventtype, elements, **kwargs):
        """
        Forwards all full syncs and single edits to clients and logs them to the data base.
        """
        record = m.ExcalidrawLogRecord(
            room_name=room_name,
            event_type=eventtype,
            user_pseudonym=self.user_room_id
        )
        record.content = elements
        await gather(
            self.send_event(eventtype, elements=elements, **kwargs),
            database_sync_to_async(record.save)())

    async def save_room(self, room_name, elements, **kwargs):
        """
        Saves the room if all submitted elements have a newser version than the saved version.

        If a submitted element happens to have an older version number than an already stored
        version of the element, nothing will be done. It is assumed, taht the clients submit
        storage requests often enogh so that not too much data will be lost if this happens.
        This is because the author wants the element reconciliation always to be executed on
        the client side and not both, the client and the server. The clients should instead
        ensure that a ``full_sync`` happens often enough.

        Deleted elements will not be saved.
        """
        old_room, created = await get_or_create_room(room_name=room_name)
        old_room_versions = {e['id']: e['version'] for e in old_room.elements}
        elements = [e for e in elements if not e.get('isDeleted', False)]

        differences_detected = False

        if not created:
            for e in elements:
                old_version = old_room_versions.get(e['id'], -1)
                if old_version > e['version']:
                    return
                # no difference if version is equal.
                differences_detected = differences_detected or old_version < e['version']

        if not differences_detected:
            return

        elements, _ = dump_content(elements)
        room, _ = await upsert_room(
            room_name=room_name,
            defaults={'_elements': elements})
        logger.debug("room %s saved", room.room_name)

    async def send_event(self, eventtype, **event_args):
        """
        Helper to forward messages to other clients using channel layers.
        """
        await self.channel_layer.group_send(self.group_name, {
            'type': 'notify_client',
            'notification': {
                'eventtype': eventtype,
                **event_args
            },
            'sender': self.user_room_id
        })

    async def notify_client(self, event: dict):
        """
        Receives broadcast commissions for notifying clients.
        """
        # dont't send the event back to the sender
        if event['sender'] != self.user_room_id:
            await self.send_json(event['notification'])
