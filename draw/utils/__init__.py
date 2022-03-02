"""
Helper functions and classes that don't need any configured state or django stuff loaded.
"""
import json
import logging
import random
import string
import uuid
import zlib
from enum import Enum
from hashlib import sha256
from pprint import pformat
from typing import Any, Callable, Generic, List, Optional, Protocol, Tuple, TypeVar, Union, cast

from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponseForbidden
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
    ``.obj``.If any of the items or attributes in the getter chain contains ``None``,
    ``.obj`` will be None, too.
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

def reverse_with_query(viewname, kwargs=None, query_kwargs=None):
    """
    Custom reverse to add a query string after the url
    Example usage::

        url = my_reverse('my_test_url', kwargs={'pk': object.id},
                         query_kwargs={'next': reverse('home')})
    """
    # from https://stackoverflow.com/questions/4995279/
    # including-a-querystring-in-a-django-core-urlresolvers-reverse-call#4995467
    url = reverse(viewname, kwargs=kwargs)

    if query_kwargs:
        return f"{url}?{urlencode(query_kwargs)}"

    return url

@sync_to_async
def user_is_staff(user):
    return user.is_superuser or user.is_staff

def require_staff_user(async_func):
    async def inner(request: HttpRequest, *args, **kwargs):
        if not await user_is_staff(request.user):
            return HttpResponseForbidden(_("You need to be logged in as staff or as admin."))
        return await async_func(request, *args, **kwargs)
    return inner

@sync_to_async
def user_is_authenticated(user):
    return user.is_authenticated

@sync_to_async
def user_is_authorized(user, room):
    return user.is_authenticated and (
        user.is_staff
        or user.is_superuser
        or not room.room_consumer_id
        or user.registered_via_id == room.room_consumer_id)

def require_login(async_func):
    async def inner(request: HttpRequest, *args, **kwargs):
        if not await user_is_authenticated(request.user):
            return HttpResponseForbidden(_("You need to be logged in."))
        return await async_func(request, *args, **kwargs)
    return inner

JSONType = Optional[Union[dict, list, str, int, float]]

def load_content(content: bytes, compressed: bool = True) -> JSONType:
    if compressed:
        return json.loads(zlib.decompress(content).decode('utf-8'))
    return json.loads(content.decode('utf-8'))

def dump_content(content: JSONType, force_compression=False) -> Tuple[bytes, bool]:
    val_bytes = json.dumps(content, ensure_ascii=False).encode('utf-8')
    compressed = zlib.compress(val_bytes)
    if force_compression or len(compressed) < len(val_bytes):
        return compressed, True
    return val_bytes, False

def flatten_list(l: list):
    return [flatten_list(e) if isinstance(e, list) else e for e in l]

def user_id_for_room(uid: uuid.UUID, room_name: str):
    return sha256(uid.bytes + b":" + room_name.encode('utf-8')).hexdigest()

def make_room_name(length):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def absolute_reverse(request: HttpRequest, *args, **kwargs):
    return request.build_absolute_uri(reverse(*args, **kwargs))

lazy_pformat = lazy(pformat, str)


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