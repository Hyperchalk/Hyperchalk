import asyncio
import logging
import uuid
from asyncio import gather
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from typing import List, Optional, Set

from channels.db import database_sync_to_async
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils.timezone import now
from faker import Faker

from draw.utils import Chain, dump_content, user_id_for_room
from draw.utils.auth import user_is_authenticated, user_is_authorized, user_is_staff
from draw.utils.django_loaded import LoggingAsyncJsonWebsocketConsumer
from ltiapi.models import CustomUser

from . import models as m

logger = logging.getLogger("draw.collab")

create_record = database_sync_to_async(m.ExcalidrawLogRecord.objects.create)
bulk_create_records = database_sync_to_async(m.ExcalidrawLogRecord.objects.bulk_create)
upsert_room = database_sync_to_async(m.ExcalidrawRoom.objects.update_or_create)
get_or_create_room = database_sync_to_async(m.ExcalidrawRoom.objects.get_or_create)
auth_room = database_sync_to_async(
    m.ExcalidrawRoom.objects.only("room_name", "room_consumer", "tracking_enabled").get_or_create)
stored_pseudonym_for_user_in_room = database_sync_to_async(
    m.Pseudonym.stored_pseudonym_for_user_in_room)

@database_sync_to_async
def get_known_file_ids(room_name: str):
    return {
        element_file_id for (element_file_id,)
        in m.ExcalidrawFile.objects
            .filter(belongs_to=room_name)\
            .values_list('element_file_id')}

@database_sync_to_async
def user_name(user):
    return user.username


class CollaborationConsumer(LoggingAsyncJsonWebsocketConsumer):
    allowed_eventtypes = {
        'collaborator_change', 'elements_changed',
        'save_room', 'full_sync', 'files_added'}
    channel_layer_namespace = 'draw_room_'

    def create_task(self, coro, *, name=None):
        """
        we store the task in a set so it does not get garbage collected. See the important note
        in the docs: https://docs.python.org/3.11/library/asyncio-task.html#asyncio.create_task

        The params are the same as for ``asyncio.create_task()``.

        TODO: add context param in python 3.11
        """
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tasks: Set[asyncio.Task] = set()

    # region connection handling
    async def connect(self):
        # pylint: disable=attribute-defined-outside-init
        self.kwargs = self.scope['url_route']['kwargs']
        self.user: CustomUser = self.scope['user']
        self.room_name = self.kwargs['room_name']
        room, _ = await auth_room(room_name=self.room_name)
        self.tracking_enabled = room.tracking_enabled

        authenticated, authorized = await gather(
            user_is_authenticated(self.user),
            user_is_authorized(self.user, room, self.scope.get("session")))
        if (not settings.ALLOW_ANONYMOUS_VISITS
            and self.room_name not in settings.PUBLIC_ROOMS
            and not authenticated
            and not authorized
        ):
            _, username = await gather(
                super().connect(),
                user_name(self.user)
            )
            who = 'Someone' if not authenticated else username
            reason = (
                'anonymous visits are disallowed.'
                if not authenticated
                else 'this user is not allowed to access the room.')
            logger.warning(
                '%(who)s tried to enter room %(room)s without logging in, but %(reason)s',
                {'who': who, 'room': self.room_name, 'reason': reason})
            await self.send_json({'eventtype': 'login_required'})
            return await self.disconnect(3000)

        self.user_room_id = (await stored_pseudonym_for_user_in_room(self.user, room)) \
            if self.user.id is not None \
            else user_id_for_room(uuid.uuid4(), self.room_name)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        connect = await super().connect()

        if self.tracking_enabled:
            # the record can be created some time around here. we don't need to wait for that. but this
            # should only be stored if the connection was successful. it would be nice if this entry
            # would be the first one. however, collabotaror changes may be stored with the created_at
            # datetime being at some point back in time. this happens if the client collected data while
            # the connection has not been established yet. therefore, it just doesn't matter if the room
            # entry record is stored as the first consumer event. it's just a nice data point to have.
            self.create_task(create_record(
                room_name=self.room_name,
                event_type='collaborator_entered',
                user_pseudonym=self.user_room_id,
                _content=b'null',
                _compressed=False))

        return connect

    async def disconnect(self, code):
        """
        Notify all collaborators if a client left, so they
        can remove it from their collaborator list, too.
        """
        disconnect = await super().disconnect(code)
        if code != 3000:
            # it is not mandatory to wait for these. it just needs
            # to be done at some point in the near future.
            self.create_task(self.notify_collaborators_about_leaving())
            if self.tracking_enabled:
                self.create_task(create_record(
                    room_name=self.room_name,
                    event_type='collaborator_left',
                    user_pseudonym=self.user_room_id,
                    _content=b'null',
                    _compressed=False))
        return disconnect

    async def notify_collaborators_about_leaving(self):
        """
        notifiy collaborators about leaving the room and leave the channel layer
        """
        await self.send_event(
            'collaborator_left', collaborator={'userRoomId': self.user_room_id})
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
    # endregion connection handling

    # region user actions
    async def collaborator_change(self, room_name, eventtype, changes: List[dict], **kwargs):
        """
        Forwards all updates to users and their pointers to clients and logs them to the data base.
        """
        # logger.debug("called collaborator_change")
        collaborator_to_send = deepcopy(changes[-1])

        if self.tracking_enabled:
            # the reference datetime is calculated on the server so that we
            # don't have to rely on the client to send the correct datetime.
            # only the time delta of the client actions need to be correct.
            client_reference_dt = collaborator_to_send.get('time', None)
            client_reference_dt = parse_datetime(client_reference_dt) if client_reference_dt else now()
            now_dt = now()

            records = []

            for change in changes:
                del change['username']

                # time recalculation happens here.
                client_dt = change.pop('time', None)
                client_dt = parse_datetime(client_dt) if client_dt else now()
                delta = client_reference_dt - client_dt

                record = m.ExcalidrawLogRecord(
                    room_name=room_name,
                    event_type=eventtype,
                    user_pseudonym=self.user_room_id,
                    created_at=now_dt - delta)
                record.content = change
                records.append(record)

            self.create_task(bulk_create_records(records))

        collaborator_to_send['userRoomId'] = self.user_room_id
        self.create_task(self.send_event(eventtype, changes=[collaborator_to_send]))

    async def full_sync(self, room_name, eventtype, elements, **kwargs):
        """
        Forwards all full syncs to clients, logs them to the data base ~~and saves the room~~.
        """
        await self.elements_changed(room_name, eventtype, elements=elements, **kwargs)

    async def elements_changed(self, room_name, eventtype, elements, **kwargs):
        """
        Forwards all full syncs and single edits to clients and logs them to the data base.
        """
        if self.tracking_enabled:
            record = m.ExcalidrawLogRecord(
                room_name=room_name,
                event_type=eventtype,
                user_pseudonym=self.user_room_id
            )
            record.content = elements
            await gather(
                self.send_event(eventtype, elements=elements, **kwargs),
                database_sync_to_async(record.save)())
        else:
            await self.send_event(eventtype, elements=elements, **kwargs)

    async def files_added(self, room_name, eventtype, fileids: List[str], **kwargs):
        """
        Saves and forwards files that are newly added to the scene.

        This event is not logged to the database as new files can also be detected when a file
        element with a new file ID is added.
        """
        await self.send_event(eventtype, fileids=fileids)

    async def maybe_request_missing_files(self, room_name, file_ids_known_by_client: Set[str]):
        """
        Checks if any files from the request are missing and asks the client to send those.
        """
        known_files = await get_known_file_ids(room_name)
        missing_files = file_ids_known_by_client.difference(known_files)
        if missing_files:
            await self.send_json({
                'eventtype': 'files_missing',
                'missing': list(missing_files)})

    async def save_room(self, room_name, elements, **kwargs):
        """
        Saves the room if all submitted elements have a newer or equal version than the saved version.

        If a submitted element happens to have an older version number than an already stored
        version of the element, nothing will be done. It is assumed, taht the clients submit
        storage requests often enogh so that not too much data will be lost if this happens.
        This is because the author wants the element reconciliation always to be executed on
        the client side and not both, the client and the server. The clients should instead
        ensure that a ``full_sync`` happens often enough.

        Deleted elements will not be saved.
        """
        old_room, created = await get_or_create_room(room_name=room_name)
        old_versions = {e['id']: e['version'] for e in old_room.elements}

        differences_detected = False

        if not created:
            for e in elements:
                old_version = old_versions.get(e['id'], -1)
                if old_version > e['version']:
                    # stop when an old version is newer. the reconciliation algo for merging the
                    # elements is executed on the client side. clients should send a new save_room
                    # event after merging the state, updating all elements to their newset versions.
                    # deleted items have to be stored so the reconciliation algo can detect them
                    # and delete them on the client side. if the server would delete them here,
                    # the client would not know that the element was deleted and would not be able
                    # to delete it on the client side.
                    return
                differences_detected = differences_detected or old_version < e['version']
        else:
            differences_detected = True

        if differences_detected:
            known_file_ids = set(e['fileId'] for e in elements if 'fileId' in e)

            elements_to_store, _ = dump_content(elements, force_compression=True)
            room_tuple, _ = await gather(
                upsert_room(room_name=room_name, defaults={'_elements': elements_to_store}),
                self.maybe_request_missing_files(room_name, known_file_ids))
            room, _ = room_tuple
            logger.debug("room %s saved", room.room_name)
    # endregion user actions

    # region channel layer handling
    @property
    def group_name(self):
        """ Group name for channel layer communication """
        return self.channel_layer_namespace + self.room_name

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
            'sender': self.channel_name
        })

    async def notify_client(self, event: dict):
        """
        Receives broadcast commissions for notifying clients.
        """
        # dont't send the event back to the sender
        if event['sender'] != self.channel_name:
            await self.send_json(event['notification'])
    # endregion channel layer handling


get_log_record = database_sync_to_async(m.ExcalidrawLogRecord.objects.get)

@database_sync_to_async
def get_log_record_info_for_room(room_name):
    return list(m.ExcalidrawLogRecord.objects
        .filter(room_name=room_name)
        .order_by('created_at')
        .values_list('id', 'created_at'))

MAX_WAIT_TIME = timedelta(milliseconds=settings.BROADCAST_RESOLUTION_THROTTLE_MSEC)


class ReplayConsumer(LoggingAsyncJsonWebsocketConsumer):
    # pylint: disable=attribute-defined-outside-init
    allowed_eventtypes = {'start_replay', 'pause_replay', 'restart_replay'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tasks: Set[asyncio.Task] = set()

    def create_task(self, coro, *, name=None):
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def connect(self):
        self.user: CustomUser = self.scope.get('user')
        if not await user_is_staff(self.user):
            return await self.disconnect(3000)

        url_route: dict = self.scope.get('url_route')
        self.room_name = url_route['kwargs']['room_name']

        # this will be fun :)
        faker = Faker()
        self.encountered_user_pseudonyms = defaultdict(faker.name)

        # ensure that the task is not canceled while sending a message but only while sleeping.
        self.message_was_sent_condition = asyncio.Condition()

        await super().connect()
        await self.send_json({'eventtype': 'pause_replay'}) # reset the control button on connect


    async def receive_json(self, content, *args, **kwargs):
        """
        Received messages that are unknown are logged but don't throw an exception.
        """
        try:
            await super().receive_json(content, *args, **kwargs)
        except ValueError as e:
            logger.debug(e)

    async def disconnect(self, code):
        if await self.cancel_replay_task():
            logger.debug('client disconnected before replay of room %s finished.', self.room_name)
        return await super().disconnect(code)

    async def cancel_replay_task(self) -> bool:
        """
        Waits until the replay task can be canceled (i.e. while it sleeps) and does that.

        :returns: if a task was canceled
        """
        if hasattr(self, 'replay_task') and hasattr(self, 'message_was_sent_condition'):
            async with self.message_was_sent_condition:
                self.replay_task.cancel()
            return True
        return False

    async def init_replay(self):
        self.log_record_info = await get_log_record_info_for_room(room_name=self.room_name)

        prev_record_time = self.log_record_info[0][1]
        delta = timedelta(0)
        for _, curr_record_time in self.log_record_info[1:]:
            delta += min(MAX_WAIT_TIME, curr_record_time - prev_record_time)
            prev_record_time = curr_record_time
        duration = int(delta.total_seconds() * 1000)

        logger.debug("replay initialized. duration: %d", duration)

        await self.send_json({
            'eventtype': 'reset_scene',
            'duration': duration,
        })

    async def start_replay(self, *args, **kwargs):
        logger.info('start replay mode for room %s', self.room_name)
        if not getattr(self, 'log_record_info', []):
            await self.init_replay()
        self.replay_task = self.create_task(self.send_then_wait())
        await self.send_json({'eventtype': 'start_replay'})

    async def pause_replay(self, *args, **kwargs):
        if await self.cancel_replay_task():
            logger.debug('replay for room %s paused.', self.room_name)
            await self.send_json({'eventtype': 'pause_replay'})

    async def restart_replay(self, *args, **kwargs):
        logger.debug('restart replay of room %s', self.room_name)
        await self.cancel_replay_task()
        await self.init_replay()
        await self.start_replay()

    async def send_next_event(self):
        log_id, _ = self.log_record_info.pop(0)
        record: m.ExcalidrawLogRecord = await get_log_record(pk=log_id)
        if record.event_type in ['full_sync', 'elements_changed']:
            await self.send_json({
                'eventtype': record.event_type,
                'elements': record.content,
            })
        elif record.event_type == 'collaborator_change':
            await self.send_json({
                'eventtype': 'collaborator_change',
                'changes': [{
                    **record.content,
                    'username': self.encountered_user_pseudonyms[record.user_pseudonym],
                    'userRoomId': record.user_pseudonym,
                }]
            })

    async def send_then_wait(self):
        if self.log_record_info:
            recs = Chain(self)['log_record_info']
            current_timestamp: datetime = recs[0][1]()
            next_timestamp: Optional[datetime] = recs[1][1]()
            sleep_time = \
                min(MAX_WAIT_TIME, next_timestamp - current_timestamp) \
                if next_timestamp else timedelta(0)

            async with self.message_was_sent_condition:
                await self.send_next_event()
                # print(
                #     f'sent event. {len(self.log_record_info)} events remain. will '
                #     f'sleep for {sleep_time.total_seconds():.2f} seconds.         ',
                #     end="\r", file=sys.stderr)
            await asyncio.sleep(sleep_time.total_seconds())
            self.replay_task = self.create_task(self.send_then_wait())
        else:
            # print(file=sys.stderr)
            async with self.message_was_sent_condition:
                await self.send_json({'eventtype': 'pause_replay'})
