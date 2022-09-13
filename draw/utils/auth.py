from functools import wraps
from typing import Callable, Protocol, Union

from asgiref.sync import sync_to_async
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.contrib.sessions.backends.base import SessionBase
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, JsonResponse
from django.utils.translation import gettext_lazy as _

User = Union[AbstractBaseUser, AnonymousUser]


class Room(Protocol):
    room_consumer_id: int
    room_course_id: str


class Unauthenticated(PermissionDenied):
    pass


class Unauthorized(PermissionDenied):
    pass


def create_json_response_forbidden(e: PermissionDenied):
    return JsonResponse({'detail': str(e)}, status=403)


def create_html_response_forbidden(e: PermissionDenied):
    return HttpResponseForbidden(e)


@sync_to_async
def user_is_staff(user: User):
    return user.is_superuser or user.is_staff


async def staff_access_check(request: HttpRequest, *args, **kwargs):
    if not await user_is_staff(request.user):
        raise PermissionDenied(
            _("You need to be logged in as staff or as admin."))


def require_staff_user(json=False):
    """
    Creates an async decorator for testing if the current user is a staff user.

    Decorator is to be applied to view functions. Works
    with both django views and django ninja routes.

    :param json: whether to return a ``JsonResponse``, defaults to False
    :type json: bool, optional
    """
    create_response = create_json_response_forbidden if json else create_html_response_forbidden

    def decorator(async_func: Callable[..., HttpResponse]):

        @wraps(async_func)
        async def inner(request: HttpRequest, *args, **kwargs):
            try:
                await staff_access_check(request)
                return await async_func(request, *args, **kwargs)
            except PermissionDenied as e:
                return create_response(e)

        return inner

    return decorator


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

    # is_authenticated is needed because AnonymousUser don't has the attrs below.
    return user.is_authenticated and (
        (user.is_staff and user.has_perm("collab.view_excalidrawroom"))
        or user.is_superuser
        or room.room_consumer_id is None
        or (user.registered_via_id == room.room_consumer_id
            and (room.room_course_id is None or room.room_course_id in allowed_course_ids)))


def require_login(async_func: Callable[..., HttpResponse]):
    """
    Async decorator to test is the user is logged in.
    """

    @wraps(async_func)
    async def inner(request: HttpRequest, *args, **kwargs):
        if not await user_is_authenticated(request.user):
            return HttpResponseForbidden(_("You need to be logged in."))
        return await async_func(request, *args, **kwargs)

    return inner


@require_staff_user()
async def user_is_staff_view(request):
    return HttpResponse('', status=200)
