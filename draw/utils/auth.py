from typing import Callable, Protocol, Union

from asgiref.sync import sync_to_async
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.contrib.sessions.backends.base import SessionBase
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.utils.translation import gettext_lazy as _

User = Union[AbstractBaseUser, AnonymousUser]

class Room(Protocol):
    room_consumer_id: int
    room_course_id: str

@sync_to_async
def user_is_staff(user: User):
    return user.is_superuser or user.is_staff

def require_staff_user(async_func: Callable[..., HttpResponse]):
    async def inner(request: HttpRequest, *args, **kwargs):
        if not await user_is_staff(request.user):
            return HttpResponseForbidden(_("You need to be logged in as staff or as admin."))
        return await async_func(request, *args, **kwargs)
    return inner

@sync_to_async
def user_is_authenticated(user: User) -> bool:
    return user.is_authenticated

@sync_to_async
def user_is_authorized(user: User, room: Room, session: SessionBase) -> bool:
    """
    Tests if the user is authorized to access a room.
    """
    # the course_id is set, when the user clicks a deep link. it is always submitted in a signed
    # token from the LMS. the deep linking message launch then sets it on the session for internal
    # usage. this has the advantage that the users courses don't have to be saved to the database
    # if the session middleware is cookie based.
    allowed_course_ids = session.get('course_ids', [])

    return user.is_authenticated and (
        user.is_staff
        or user.is_superuser
        or room.room_consumer_id is None
        or (user.registered_via_id == room.room_consumer_id
            and (room.room_course_id is None or room.room_course_id in allowed_course_ids)))

def require_login(async_func: Callable[..., HttpResponse]):
    async def inner(request: HttpRequest, *args, **kwargs):
        if not await user_is_authenticated(request.user):
            return HttpResponseForbidden(_("You need to be logged in."))
        return await async_func(request, *args, **kwargs)
    return inner
