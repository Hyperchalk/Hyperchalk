import logging
import traceback
from typing import Optional, Set
from urllib.parse import urlunsplit

from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings


def build_absolute_uri_without_request(
    url: str, query: str = '', host: str = settings.LINK_BASE,
    protocol: Optional[str] = 'https'
):
    """
    Gives the absolute URI of a resource after reversing.

    ``request.build_absolute_uri()`` should be used for this usually, but somtimes the
    ``request`` is not available.

    :param url: a site-relative url

    :param query: the url query string. Defaults to an empty string.

    :param host: the current host. defaults to ``settings.LINK_BASE``.

    :param protocol: you can specify a protocol (``http(s)``) here. Defaults to ``https``.
    """
    return urlunsplit((protocol, host, url, query, None))


websocket_logger = logging.getLogger('draw.websocket')


class LoggingAsyncJsonWebsocketConsumer(AsyncJsonWebsocketConsumer):
    """
    Same as :class:`channels.generic.websocket.AsyncJsonWebsocketConsumer`
    except that it logs exceptions to the console.

    You can configure the log by changing the logger config for `draw.websocket`
    """
    allowed_eventtypes: Set[str] = set()

    async def webscoket_receive(self, message):
        """
        Catch and log exceptions to the console as this is no default in django channels.
        """
        try:
            return await super().receive(message)
        except Exception as e:
            websocket_logger.error("\n".join(traceback.format_exception(e)))
            raise e from e

    async def websocket_connect(self, message):
        try:
            return await super().websocket_connect(message)
        except Exception as e:
            websocket_logger.error("\n".join(traceback.format_exception(e)))
            raise e from e

    async def websocket_disconnect(self, message):
        try:
            return await super().websocket_disconnect(message)
        except Exception as e:
            if not isinstance(e, (StopConsumer,)):
                websocket_logger.error("\n".join(traceback.format_exception(e)))
            raise e from e

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
            return await method(**content, **kwargs, **getattr(self, 'kwargs', dict()))
        raise ValueError(f'The eventtype "{msg_type}" is not allowed.')
