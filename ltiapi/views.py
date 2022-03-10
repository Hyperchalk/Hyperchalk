import asyncio
import logging
from typing import List, Optional

import aiohttp
from asgiref.sync import async_to_sync, sync_to_async
from django.contrib.auth import get_user_model, login
from django.http import (HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden,
                         JsonResponse)
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import classonlymethod
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoMessageLaunch, DjangoOIDCLogin
from pylti1p3.contrib.django.lti1p3_tool_config import DjangoDbToolConf
from pylti1p3.deep_link_resource import DeepLinkResource

from collab.models import ExcalidrawRoom
from draw.utils import absolute_reverse, make_room_name
from draw.utils.auth import user_is_authorized

from . import models as m
from .utils import (get_launch_url, issuer_namespaced_username, lti_registration_data,
                    make_tool_config_from_openid_config_via_link)

logger = logging.getLogger("draw.ltiapi")


class RegisterConsumerView(DetailView):
    """
    This View implements LTI Advantage Automatic registration. It supports GET for the user
    to control the configuration steps and POST, which starts the consumer configuration.
    """
    template_name = 'ltiapi/register_consumer_start.html'
    end_template_name = 'ltiapi/register_consumer_result.html'
    model = m.OneOffRegistrationLink
    context_object_name = 'link'

    def get_template_names(self) -> List[str]:
        if self.request.method == 'POST':
            return [self.end_template_name]
        return [self.template_name]

    @classonlymethod
    def as_view(cls, **initkwargs):
        # this needs to be "hacked", so that the class view supports async views.
        view = super().as_view(**initkwargs)
        # pylint: disable=protected-access
        view._is_coroutine = asyncio.coroutines._is_coroutine
        return view

    # pylint: disable = invalid-overridden-method, attribute-defined-outside-init
    async def get(self, request: HttpRequest, *args, **kwargs):
        return await sync_to_async(super().get)(request, *args, **kwargs) # type: ignore

    async def post(self, request: HttpRequest, *args, **kwargs):
        """
        Register the application at the provider via the LTI registration flow.

        The configuration flow is well explained at https://moodlelti.theedtech.dev/dynreg/
        """
        # verify that the registration link is unused
        self.object = reg_link = await sync_to_async(self.get_object)() # type: ignore
        if reg_link.registered_consumer is not None:
            ctx = {'error': _(
                'The registration link has already been used. Please ask '
                'the admin of the LTI app for a new registration link.')}
            return self.render_to_response(context=ctx)

        # prepare for getting data about the consumer
        openid_config_endpoint = request.GET.get('openid_configuration')
        jwt_str = request.GET.get('registration_token')

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
            consumer = await make_tool_config_from_openid_config_via_link(
                openid_config, openid_registration, reg_link)
        except AssertionError as e:
            # error if the data from the consumer is missing mandatory information
            ctx = self.get_context_data(registration_success=False, error=e)
            return self.render_to_response(ctx, status=406)

        await sync_to_async(reg_link.registration_complete)(consumer)

        logging.info(
            'Registration of issuer "%s" with client %s complete',
            consumer.issuer, consumer.client_id)
        ctx = self.get_context_data(registration_success=True)
        return self.render_to_response(ctx)


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
    message_launch_data = message_launch.get_launch_data()

    # log the user in. if this is the user's first visit, save them to the database before.
    # 1) extract user information from the data passed by the consumer
    username = message_launch_data\
        .get('https://purl.imsglobal.org/spec/lti/claim/ext', {})\
        .get('user_username') # type: ignore
    issuer = message_launch_data['iss']
    client_id = message_launch_data['aud']
    user_full_name = message_launch_data.get('name', '')
    username = issuer_namespaced_username(issuer, username)
    lti_tool = tool_conf.get_lti_tool(issuer, client_id)

    # 2) get / create the user from the db and log them in
    UserModel = get_user_model()
    user, user_mod = UserModel.objects.get_or_create(username=username)
    if not user.first_name:
        user.first_name = user_full_name
        user_mod = True
    if user.registered_via_id != lti_tool.pk:
        # needed if tool was re-registered. otherwise trying
        # to save the user would raise an IngrityError.
        user.registered_via = lti_tool
        user_mod = True
    if user_mod:
        user.save()
    login(request, user)

    # room and course information are needed for every launch type.
    room_name = message_launch_data\
        .get('https://purl.imsglobal.org/spec/lti/claim/custom', {})\
        .get('room', None) \
        or request.GET.get('room', make_room_name(24))

    room_uri = absolute_reverse(request, 'collab:room', kwargs={'room_name': room_name})

    course_context = message_launch_data\
        .get('https://purl.imsglobal.org/spec/lti/claim/context', {})
    course_id = course_context.get('id', None)

    if message_launch.is_deep_link_launch():
        # create a deep link and initialize the room
        course_title = course_context.get('title', None)
        title = message_launch_data\
            .get('https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings', {})\
            .get('title', course_title)
        title = "Draw Together" + (f" – {title}" if title else "")

        room, _ = ExcalidrawRoom.objects.get_or_create(
            room_name=room_name,
            room_created_by=user,
            room_consumer=lti_tool,
            room_course_id=course_id)
        room.save()

        resource = DeepLinkResource()
        resource.set_url(absolute_reverse(request, 'lti:launch'))\
            .set_custom_params({'room': room_name})\
            .set_title(title)

        html = message_launch.get_deep_link().output_response_form([resource])
        return HttpResponse(html)

    if message_launch.is_data_privacy_launch():
        # TODO: implement data privacy screen. (not as urgent. moodle does not support this anyway.)
        #       see issue #17
        raise NotImplementedError()

    if message_launch.is_resource_launch():
        # join the room if the user is allowed to access it.
        room = get_object_or_404(ExcalidrawRoom, room_name=room_name)
        request.session.set_expiry(0)
        request.session['course_ids'] = request.session.get('course_ids', []).append(course_id)
        if not async_to_sync(user_is_authorized)(user, room, request.session):
            return HttpResponseForbidden("You are not allowed to access this room.")
        # the data for the authorization check needs to be passed to every endpoint.
        return redirect(room_uri)

    return HttpResponseBadRequest('Unknown or unsupported message type provided.')

lti_launch.csrf_exempt = True
lti_launch.xframe_options_exempt = True
# The launch can only be triggered with a valid JWT issued by a registered platform.
