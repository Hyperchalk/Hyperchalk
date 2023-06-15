import logging
from pprint import pformat
from typing import List, Optional, cast
from uuid import UUID

import aiohttp
from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.contrib.auth import login
from django.http import (HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect,
                         JsonResponse)
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoMessageLaunch, DjangoOIDCLogin
from pylti1p3.contrib.django.lti1p3_tool_config import DjangoDbToolConf
from pylti1p3.deep_link_resource import DeepLinkResource

from collab.models import CourseToRoomMapper
from draw.utils import absolute_reverse, async_get_object_or_404, make_room_name
from draw.utils.auth import user_is_authorized

from . import models as m
from .utils import (get_course_context, get_course_id, get_custom_launch_data, get_launch_url, get_lti_tool,
                    get_room_name, get_user_from_launch_data, launched_by_superior, lti_registration_data,
                    make_tool_config_from_openid_config_via_link)

logger = logging.getLogger("draw.ltiapi")


async def start_consumer_registration(request: HttpRequest, link: m.OneOffRegistrationLink):
    """ Ask the consumer to confirm the registration of the LTI app. """
    return render(request, 'ltiapi/register_consumer_start.html', {'link': link})

def render_registration_error(request: HttpRequest, error: str, status: int = 400):
    return render(request, 'ltiapi/register_consumer_result.html', {'error': error}, status=status)

async def register_consumer(request: HttpRequest, link: m.OneOffRegistrationLink):
    """ This is executed when the consumer confirms the registration of the LTI app. """
    if link.registered_consumer is not None:
        return render_registration_error(
            request,
            _('The registration link has already been used. Please ask '
              'the admin of the LTI app for a new registration link.'),
            status=403)

    # prepare for getting data about the consumer
    openid_config_endpoint = request.GET.get('openid_configuration')
    jwt_str = request.GET.get('registration_token')

    if not openid_config_endpoint:
        logger.warning(
            "a client tried to register but did not supply the proper parameters. The supplied "
            "parameters are:\n%s", pformat(request.GET.lists))
        return render_registration_error(
            request,
            _("No configuration endpoint was found in the parameters. Are you trying to "
              "register a legacy LTI consumer? This app only supports LTI 1.3 Advantage."))

    async with aiohttp.ClientSession() as session:
        # get information about how to register to the consumer
        logger.info('Getting registration data from "%s"', openid_config_endpoint)
        resp = await session.get(openid_config_endpoint)
        openid_config = await resp.json()

        # send registration to the consumer
        tool_provider_registration_endpoint = openid_config['registration_endpoint']
        registration_data = lti_registration_data(request)
        logger.info('Registering tool at "%s"', tool_provider_registration_endpoint)
        resp = await session.post(
            tool_provider_registration_endpoint,
            json=registration_data,
            headers={
                'Authorization': 'Bearer ' + jwt_str,
                'Accept': 'application/json'
            })
        openid_registration = await resp.json()
    try:
        # use the information about the registration to regsiter the consumer to this app
        consumer = await make_tool_config_from_openid_config_via_link(openid_config, openid_registration, link)
    except AssertionError as e:
        # error if the data from the consumer is missing mandatory information
        logger.warning('Registration failed: %s', e)
        return render_registration_error(request, e.args[0])

    await sync_to_async(link.registration_complete)(consumer)

    logging.info(
        'Registration of issuer "%s" with client %s complete',
        consumer.issuer, consumer.client_id)
    return render(request, 'ltiapi/register_consumer_result.html', {'link': link, 'registration_success': True})


async def dynamic_consumer_registration(request: HttpRequest, link: UUID):
    """
    This View implements LTI Advantage Automatic registration. It supports GET for the user
    to control the configuration steps and POST, which starts the consumer configuration.
    """
    link_obj = await async_get_object_or_404(m.OneOffRegistrationLink, id=link)
    if request.method == "GET":
        return await start_consumer_registration(request, link_obj)
    else:
        return await register_consumer(request, link_obj)
dynamic_consumer_registration.csrf_exempt = True # type: ignore
dynamic_consumer_registration.xframe_options_exempt = True # type: ignore


async def oidc_jwks(
    request: HttpRequest, issuer: Optional[str] = None,
    client_id: Optional[str] = None
):
    """ JWT signature delivery endpoint """
    tool_conf = DjangoDbToolConf()
    get_jwks = sync_to_async(tool_conf.get_jwks)
    return JsonResponse(await get_jwks(issuer, client_id))


def oidc_login(request: HttpRequest):
    """
    This just verifies that the requesting consumer is allowed to log in and tells the consumer,
    where to go next. The actual user login happens when the LTI launch is performed.
    """
    tool_conf = DjangoDbToolConf()
    launch_data_storage = DjangoCacheDataStorage()

    oidc_login_handle = DjangoOIDCLogin(request, tool_conf, launch_data_storage=launch_data_storage)
    target_link_uri = get_launch_url(request)
    oidc_redirect = oidc_login_handle\
        .enable_check_cookies()\
        .redirect(target_link_uri, False)
    return oidc_redirect

oidc_login.csrf_exempt = True # type: ignore
oidc_login.xframe_options_exempt = True # type: ignore
# XXX: what caould go wrong if an attacker would trigger the login
#      for a known issuer? could they somehow change a deeplink?
# YYY: → is the OIDC login flow csrf-safe? there is no possibility
#      to pass a valid csrf token by the LTI Platform though...
# TODO: it would be nice to have the referrer check logic from the
#       csrf middleware here so at least this could be checked.

@require_POST
def lti_configure(request: HttpRequest, launch_id: str):
    tool_conf = DjangoDbToolConf()
    launch_data_storage = DjangoCacheDataStorage()
    message_launch = DjangoMessageLaunch.from_cache(
        launch_id, request, tool_conf, launch_data_storage=launch_data_storage)
    message_launch_data = cast(dict, message_launch.get_launch_data())
    lti_tool = get_lti_tool(tool_conf, message_launch_data)

    user = get_user_from_launch_data(message_launch_data, lti_tool)
    login(request, user)

    # create a deep link and initialize the room
    course_title = get_course_context(message_launch_data).get('title', None)
    title = message_launch_data\
        .get('https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings', {})\
        .get('title', course_title)
    title = "Hyperchalk" + (f" – {title}" if title else "")
    mode = request.POST.get("mode")

    def upsert_room_mappers(room_names: List[str]):
        for room_name in room_names:
            CourseToRoomMapper.objects.create_from_room_name(
                lti_data_room=room_name,
                course_id=get_course_id(message_launch_data),
                mode=mode,
                user=request.user,
                lti_tool=lti_tool)

    resource = DeepLinkResource().set_url(absolute_reverse(request, 'lti:launch'))
    # needed when the config is updated

    Modes = CourseToRoomMapper.BoardMode

    if mode == Modes.CLASSROOM:
        room_name = make_room_name(24)
        upsert_room_mappers([room_name])
        resource.set_title(title).set_custom_params({'mode': mode, 'room': room_name})

    elif mode == Modes.GROUPWORK:
        n_groups = int(request.POST.get('n-groups'))
        if n_groups > 50:
            logger.warning(
                _("User %s tried to create a board with more than %d groups"),
                user.username, settings.MAX_GROUPS)
            return HttpResponseForbidden(
                _("There can't be more than %d groups.") % (settings.MAX_GROUPS))

        existing_groups = request.POST.get('groups', None)
        existing_groups = existing_groups.split(",") if existing_groups else []
        if len(existing_groups) > n_groups:
            logger.warning(
                _("User %s tried to create a board with less groups than what already existed."),
                user.username, settings.MAX_GROUPS)
            return HttpResponseBadRequest(
                _("The number of groups you specified "
                  "is smaller than the groups that currenty exist."
                ) % (settings.MAX_GROUPS))

        room_names = [make_room_name(24) for _ in range(n_groups - len(existing_groups))]
        upsert_room_mappers(room_names)
        resource.set_title(title + " – " + Modes.GROUPWORK.label)\
            .set_custom_params({'mode': mode, 'rooms': ",".join(room_names)})

    elif mode == Modes.STUDENT:
        resource.set_title(title + " – " + Modes.STUDENT.label)\
            .set_custom_params({'mode': mode, 'room': make_room_name(24)})

    else:
        logger.warning(_("User %s tried to request an illegal board mode."), user.username)
        return HttpResponseBadRequest(_("The mode you requested does not exist."))

    return HttpResponse(message_launch.get_deep_link().output_response_form([resource]))


@require_POST
def lti_launch(request: HttpRequest):
    """
    Implements the LTI launch. It logs the user in and
    redirects them according to the requested launch type.
    """
    # parse and verify the data that was passed by the LTI consumer
    tool_conf = DjangoDbToolConf()
    launch_data_storage = DjangoCacheDataStorage()
    message_launch = DjangoMessageLaunch(
        request, tool_conf, launch_data_storage=launch_data_storage)
    message_launch_data = cast(dict, message_launch.get_launch_data())

    custom_data = get_custom_launch_data(message_launch_data)
    lti_tool = get_lti_tool(tool_conf, message_launch_data)

    user = get_user_from_launch_data(message_launch_data, lti_tool)
    login(request, user)

    if message_launch.is_deep_link_launch():
        return render(request, 'ltiapi/configure.html', {
            'launch_id': message_launch.get_launch_id(),
            # these are needed if the config is changed.
            'rooms': custom_data.get("rooms", ""),
            'room_count': custom_data.get("rooms", "").count(",") + 1,
        })

    if message_launch.is_data_privacy_launch():
        return HttpResponseRedirect(absolute_reverse(request, 'lti:privacy'))

    if message_launch.is_resource_launch():
        # the course ids get stored to the session. one side effect of this is that a board that
        # has been visited in the context of a course once could be visited in other courses
        # contexts or with no context at all as well.
        request.session.set_expiry(0)
        allowed_course_ids = request.session.get('course_ids', [])
        course_id = get_course_id(message_launch_data)
        allowed_course_ids.append(course_id)
        request.session['course_ids'] = allowed_course_ids

        # classroom is default for legacy db entry support
        Modes = CourseToRoomMapper.BoardMode
        mode = custom_data.get('mode', Modes.CLASSROOM)

        if mode == Modes.GROUPWORK:
            # not exactly performant but it works
            room_pointers = [
                CourseToRoomMapper.objects.get_or_create_for_course(
                    lti_data_room=room_pointer_id, course_id=course_id,
                    user=user, mode=mode, lti_tool=lti_tool)
                for room_pointer_id in custom_data.get('rooms').split(",")]
            return render(request, 'ltiapi/choose_group.html', {
                'room_pointers': [pointer for pointer, created in room_pointers]
            })

        if launched_by_superior(message_launch_data) and mode in [Modes.STUDENT, Modes.STUDENT_LEGACY]:
            lti_data_room = get_room_name(request, message_launch_data)
            if mode == Modes.STUDENT:
                room_pointers = CourseToRoomMapper.objects.filter(
                    lti_data_room=lti_data_room,
                    course_id=course_id,
                    mode=mode
                )
            elif mode == Modes.STUDENT_LEGACY:
                room_pointers = CourseToRoomMapper.objects.filter(
                    lti_data_room__startswith=lti_data_room,
                    course_id=course_id,
                    mode=mode
                )
            return render(request, 'ltiapi/board_teacher_overview.html', {
                'room_pointers': room_pointers
            })

        if mode in [Modes.CLASSROOM, Modes.STUDENT, Modes.STUDENT_LEGACY]:
            lti_data_room = get_room_name(request, message_launch_data)
            # Mappers will be created automatically depending on the
            # mode. rooms that don't exist yet will also be created.
            room_pointer, __ = CourseToRoomMapper.objects.get_or_create_for_course(
                lti_data_room=lti_data_room, course_id=course_id,
                user=user, mode=mode, lti_tool=lti_tool)
            room = room_pointer.room
            room_uri = absolute_reverse(request, 'collab:room', kwargs={'room_name': room.room_name})
            # join the room if the user is allowed to access it.
            if not async_to_sync(user_is_authorized)(user, room, request.session):
                logger.warning(
                    "User %s tried to join room (%s) %s, "
                    "despite not being authorized.", user, mode, room)
                return HttpResponseForbidden("You are not allowed to access this room.")
            return redirect(room_uri)

        return HttpResponseBadRequest(_("Invalid assignment type."))

    return HttpResponseBadRequest(_('Unknown or unsupported message type provided.'))

lti_launch.csrf_exempt = True
lti_launch.xframe_options_exempt = True
# The launch can only be triggered with a valid JWT issued by a registered platform.
