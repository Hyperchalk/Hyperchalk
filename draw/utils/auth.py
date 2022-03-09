from datetime import timedelta
from typing import Callable, Optional, Protocol, Union

from asgiref.sync import sync_to_async
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.core.signing import TimestampSigner
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
def user_is_authorized(user: User, room: Room, signed_request_data: Optional[str] = None) -> bool:
    request_data = TimestampSigner().unsign_object(signed_request_data, max_age=timedelta(days=1)) \
        if signed_request_data else dict()
    # the course_id is sent, when the user clicks a deep link. it is always submitted in a signed
    # token from the LMS. the deep linking message launch then resigns it for internal usage.
    # this has the advantage that the users courses don't have to be saved to the database.
    course_id = request_data.get('course_id', None)

    return user.is_authenticated and (
        user.is_staff
        or user.is_superuser
        or room.room_consumer_id is None
        or (user.registered_via_id == room.room_consumer_id
            and (room.room_course_id is None or room.room_course_id == course_id)))

def require_login(async_func: Callable[..., HttpResponse]):
    async def inner(request: HttpRequest, *args, **kwargs):
        if not await user_is_authenticated(request.user):
            return HttpResponseForbidden(_("You need to be logged in."))
        return await async_func(request, *args, **kwargs)
    return inner
