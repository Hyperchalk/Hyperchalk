from typing import Callable, Protocol, Union
from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponseForbidden, HttpResponse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

User = Union[AbstractBaseUser, AnonymousUser]

class Room(Protocol):
    room_consumer_id: int

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
def user_is_authorized(user: User, room: Room) -> bool:
    return user.is_authenticated and (
        user.is_staff
        or user.is_superuser
        or not room.room_consumer_id
        or user.registered_via_id == room.room_consumer_id)

def require_login(async_func: Callable[..., HttpResponse]):
    async def inner(request: HttpRequest, *args, **kwargs):
        if not await user_is_authenticated(request.user):
            return HttpResponseForbidden(_("You need to be logged in."))
        return await async_func(request, *args, **kwargs)
    return inner
