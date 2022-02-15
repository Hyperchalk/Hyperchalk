from typing import Set

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from . import models as m


class CollaborationConsumer(AsyncJsonWebsocketConsumer):
    allowed_methods: Set[str] = {'consolelog'}

    async def receive_json(self, content, **kwargs):
        # msg_type = camel_to_snake(json_data['type'])
        msg_type = content['eventtype']
        # logger.debug(f'received json: {json_data} in {self.__class__.__name__}')
        if msg_type in self.allowed_methods:
            method = getattr(self, msg_type)
            return await method(**content)
        raise ValueError(f'The message type "{msg_type}" is not allowed.')

    async def consolelog(self, **kwargs):
        print(kwargs)

    async def pointer_movement(self, eventtype, pointer, **kwargs):
        m.ExcalidrawLogRecord(
            content=pointer,
            eventtype=eventtype,
            user=... # TODO: get user or pseudonym via LTI login id
        ).save()

# TODO: ...
# - store the start appstate
# - store a current appstate
# - calculate the updates between the last appstate and the current appstate
# - store only first appstate, update diffs and current appstate to the db
