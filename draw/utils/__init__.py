"""
Helper functions and classes that don't need any configured state or django stuff loaded.
"""
import base64
import json
import logging
import random
import re
import string
import uuid
import zlib
from enum import Enum
from hashlib import sha256
from pprint import pformat
from typing import (Any, Callable, Collection, Dict, Generic, Hashable, Iterable, List, Optional, Protocol, Sequence,
                    Tuple, TypeVar, Union, cast)

from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import log
from django.utils.functional import lazy
from django.utils.http import urlencode
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _


class SeqMode(Enum):
    MERGE = 1
    COMBINE = 2
    OVERRIDE = 3

StructureType = TypeVar("StructureType", dict, list, set, tuple)

# def deepmerge(first: StructureType, second: StructureType) -> StructureType:
def deepmerge(first, second, sequence_mode=SeqMode.MERGE):
    """
    Deep merges dicts, lists, tuples and sets.

    Dicts are merged by keys. Lists and tuple are appended. Sets
    will be unionized. If types in a dict don't match, the value
    in the second dict overrides the value in the first one.

    :param first: the data to be merged into

    :param second: the data to merge into ``first``

    :raises TypeError: if the types of the arguments do not match.

    :returns: a new data structure of the same type as ``first`` and ``second``.
    """
    if type(first) is not type(second):
        return second
        # raise TypeError(
        #     f"can't merge: first ({type(first)}) and second ({type(second)}) "
        #     "arguments are not of the same type.")

    if isinstance(first, dict):
        out = first.copy()
        for key, value in second.items():
            if key in out:
                out[key] = deepmerge(out[key], value, sequence_mode)
            else:
                out[key] = value
        return out

    if isinstance(first, (list, tuple)):
        if sequence_mode == SeqMode.MERGE:
            max_len = max(len(first), len(second))
            out = []
            for i in range(max_len):
                try:
                    out[i] = deepmerge(first[i], second[i], sequence_mode)
                except IndexError:
                    pass
                try:
                    out[i] = first[i]
                except IndexError:
                    pass
                try:
                    out[i] = second[i]
                except IndexError:
                    pass

            return type(first)(out)

        if sequence_mode == SeqMode.COMBINE:
            return first + second

        if sequence_mode == SeqMode.OVERRIDE:
            return second

    if isinstance(first, set):
        return first.union(second)

    raise TypeError(f"unsupported type: {type(first)}")


ChainedObj = TypeVar('ChainedObj')

class Chain(Generic[ChainedObj]):
    """
    A class for optional chaining in Python.

    Contains a tree of ``dict`` s, ``list`` s and ``object`` s, that can be queried via
    ``__getitem__`` (``[...]``). The object contained in the class can be retrieved via
    calling the ``Chain`` instance. If any of the items or attributes in the getter chain
    contains ``None``, the call return value will be ``None``, too.
    """
    def __init__(self, obj: ChainedObj) -> None:
        self.obj = obj

    def get(self, key: Any, default=None):
        if isinstance(self.obj, dict):
            return Chain(self.obj.get(key, None))
        if isinstance(self.obj, (list, tuple)) \
        and 0 <= key < len(self.obj):
            return Chain(self.obj[key])
        if isinstance(key, str):
            return Chain(getattr(self.obj, key, None))
        return Chain(default)

    __getitem__ = get

    def __call__(self) -> ChainedObj:
        return self.obj


def chain(obj: Any, members: Sequence[Any], default=None):
    """
    Optional ``Chain`` as a function. The most capable getter you have ever seen.

    :param obj: the object to wrap.

    :param args: ``Sequence`` of object members that will be used to get into the object's members.

    :returns: the seeked member or the default value.
    """
    members = list(members)
    chained = Chain(obj)
    while members:
        chained = chained[members.pop(0)]
    return chained() or default


def pick(d: dict, keys: Collection[Hashable]):
    return {k: v for k, v in d.items() if k in keys}


class StrLike(Protocol):
    def __str__(self) -> str:
        ...

def apply_middleware(*args: Union[Callable, str]):
    """
    Applies all the classes / functions given in args as arguments to the previous one.

    Use functools.partial if you want to pass further arguments.
    """
    l_args: List[Union[Callable, str]] = list(args)
    ret = l_args.pop()
    while l_args:
        middelware = l_args.pop()
        if isinstance(middelware, str):
            middelware = cast(Callable, import_string(middelware))
        ret = middelware(ret)
    return ret

def reverse_with_query(
    viewname: str, kwargs: Dict[str, Any] = None,
    query_kwargs: Dict[str, Any] =None
):
    """
    Custom reverse to add a query string after the url
    Example usage::

        url = reverse_with_query('my_test_url', kwargs={'pk': object.id},
                                 query_kwargs={'next': reverse('home')})
    """
    # from https://stackoverflow.com/questions/4995279/
    # including-a-querystring-in-a-django-core-urlresolvers-reverse-call#4995467
    url = reverse(viewname, kwargs=kwargs)

    if query_kwargs:
        return f"{url}?{urlencode(query_kwargs)}"

    return url

async_get_object_or_404 = sync_to_async(get_object_or_404)

JSONType = Optional[Union[dict, list, str, int, float]]

def load_content(content: Union[bytes, bytearray, memoryview], compressed: bool = True) -> JSONType:
    content = bytes(content)
    if compressed:
        return json.loads(zlib.decompress(content).decode('utf-8'))
    return json.loads(content.decode('utf-8'))

def dump_content(content: JSONType, force_compression=False) -> Tuple[bytes, bool]:
    val_bytes = json.dumps(content, ensure_ascii=False).encode('utf-8')
    compressed = zlib.compress(val_bytes)
    if force_compression or len(compressed) < len(val_bytes):
        return compressed, True
    return val_bytes, False

class HasCompressionInformation(Protocol):
    compressed_size: int
    uncompressed_size: int

def compression_ratio(obj: HasCompressionInformation):
    comp = 100 - obj.compressed_size / obj.uncompressed_size * 100
    return f"{comp:.2f} %"

def uncompressed_json_size(uncompressed_content: JSONType):
    return len(json.dumps(uncompressed_content, ensure_ascii=False).encode('utf-8'))

def flatten_list(l: list):
    return [flatten_list(e) if isinstance(e, list) else e for e in l]

def user_id_for_room(uid: uuid.UUID, room_name: str):
    return sha256(uid.bytes + b":" + room_name.encode('utf-8')).hexdigest()

def make_room_name(length):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

room_name_re = re.compile(r'[a-zA-Z0-9_-]{10,24}')

def validate_room_name(room_name: str):
    if not room_name_re.fullmatch(room_name):
        raise ValidationError(_("'%s' is not a valid room name.") % (room_name,))

def absolute_reverse(request: HttpRequest, *args, **kwargs):
    return request.build_absolute_uri(reverse(*args, **kwargs))

lazy_pformat = lazy(pformat, str)


class TrustedOrigins(Iterable[str]):
    """
    Iterable of trusted origins for embedding this application in iframes.

    The allowed origins should be the tools configured from the database. But since the settings
    are loaded before the database, additional settings can't be pulled from the db at this point.
    The CSRF middleware casts ``CSRF_TRUSTED_ORIGINS`` this to a ``list`` when it runs. So the
    model will be loaded precisely at this point. The allowed hosts are then the hostnames of the
    issuer field of the :model:`lti1p3_tool_config.LtiTool` configs (speak the LTI platforms).
    """
    def __init__(self) -> None:
        self.tool_model: Any = None
        self.is_connected = False
        self.issuers: Iterable[str] = []

    def connected(self, tool_model):
        self.is_connected = True
        self.tool_model = tool_model

    def update_issuers(self, additional_issuers: Iterable[str]):
        issuers = self.tool_model.objects.all().values_list('issuer')
        self.issuers = list(additional_issuers) + [issuer for (issuer,) in issuers]

    def __iter__(self):
        yield from self.issuers
        # if not self.is_connected:
        #     yield from []
        # else:
            # if not self.tool_model:
            #     lti_path = 'pylti1p3.contrib.django.lti1p3_tool_config.models.LtiTool'
            #     self.tool_model = import_string(lti_path)
            # FIXME: in the async ninja context, this does not work until StopIteration is raised.
            #        only one iteration per request seems to be called
            #        what to do if this is called from an async context? It does not work until then!
            # see #36

            # for (issuer,) in self.tool_model.objects.all().values_list('issuer'):
            #     print(f'csrf check issuer: {issuer}/')
            #     # yield urlparse(issuer).hostname
            #     yield issuer


class WebSocketFormatter(log.ServerFormatter):
    def format(self, record: logging.LogRecord):
        msg = record.msg
        lvl = record.levelno
        if lvl >= logging.CRITICAL:
            msg = self.style.ERROR(msg)
        elif lvl >= logging.ERROR:
            msg = self.style.NOTICE(msg)
        elif lvl >= logging.WARNING:
            msg = self.style.WARNING(msg)

        if self.uses_server_time() and not hasattr(record, 'server_time'):
            setattr(record, 'server_time', self.formatTime(record, self.datefmt))

        record.msg = msg
        return super().format(record)

def bytes_to_data_uri(content: bytes, mime: str):
    return f"data:{mime};base64,{base64.b64encode(content).decode('ascii')}"
