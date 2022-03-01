import asyncio
import logging
from typing import List, Optional

import aiohttp
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model, login
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.utils.decorators import classonlymethod
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoMessageLaunch, DjangoOIDCLogin
from pylti1p3.contrib.django.lti1p3_tool_config import DjangoDbToolConf
from pylti1p3.deep_link_resource import DeepLinkResource

from draw.utils import absolute_reverse, make_room_name, reverse_with_query
from collab.models import ExcalidrawRoom

from . import models as m
from .utils import (get_launch_url, issuer_namespaced_username, lti_registration_data,
                    make_tool_config_from_openid_config_via_link)

logger = logging.getLogger("draw.ltiapi")


class RegisterConsumerView(DetailView):
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
        self.object = reg_link = await sync_to_async(self.get_object)() # type: ignore
        if reg_link.registered_consumer is not None:
            ctx = {'error': _(
                'The registration link has already been used. Please ask '
                'the admin of the LTI app for a new registration link.')}
            return self.render_to_response(context=ctx)

        openid_config_endpoint = request.GET.get('openid_configuration')
        jwt_str = request.GET.get('registration_token')

        async with aiohttp.ClientSession() as session:
            logger.info('Getting registration data from "%s"', openid_config_endpoint)
            resp = await session.get(openid_config_endpoint)
            openid_config = await resp.json()

            tool_provider_registration_endpoint = openid_config['registration_endpoint']
            registration_data = lti_registration_data(request)
            logger.info('Registering tool at "%s"', tool_provider_registration_endpoint)
            # logger.info(
            #     'Registering tool at "%s" with data:\n%s',
            #     tool_provider_registration_endpoint, json.dumps(registration_data))
            resp = await session.post(
                tool_provider_registration_endpoint,
                json=registration_data,
                headers={
                    'Authorization': 'Bearer ' + jwt_str,
                    'Accept': 'application/json'
                })
            openid_registration = await resp.json()
        try:
            consumer = await make_tool_config_from_openid_config_via_link(
                openid_config, openid_registration, reg_link)
        except AssertionError as e:
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
    tool_conf = DjangoDbToolConf()
    get_jwks = sync_to_async(tool_conf.get_jwks)
    return JsonResponse(await get_jwks(issuer, client_id))


def oidc_login(request: HttpRequest):
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
    tool_conf = DjangoDbToolConf()
    launch_data_storage = DjangoCacheDataStorage()
    message_launch = DjangoMessageLaunch(
        request, tool_conf, launch_data_storage=launch_data_storage)
    message_launch_data = message_launch.get_launch_data()
    # lazy_pformat: only format the data if it will be logged.
    # logger.debug("launch with data:\n%s", lazy_pformat(message_launch_data))

    # log the user in. if this is the user's first visit, save them to the database before.
    username = message_launch_data\
        .get('https://purl.imsglobal.org/spec/lti/claim/ext', {})\
        .get('user_username') # type: ignore
    issuer = message_launch_data['iss']
    client_id = message_launch_data['aud']
    user_full_name = message_launch_data.get('name', '')
    username = issuer_namespaced_username(issuer, username)

    lti_tool = tool_conf.get_lti_tool(issuer, client_id)
    UserModel = get_user_model()
    user, user_mod = UserModel.objects.get_or_create(username=username, registered_via=lti_tool)
    if not user.first_name:
        user.first_name = user_full_name
        user_mod = True
    if user_mod:
        user.save()
    login(request, user)

    room_name = message_launch_data\
        .get('https://purl.imsglobal.org/spec/lti/claim/custom', {})\
        .get('room', None) \
        or request.GET.get('room', make_room_name(24))

    room_uri = reverse_with_query('collab:index', query_kwargs={'room': room_name})
    room_uri = request.build_absolute_uri(room_uri)


    if message_launch.is_deep_link_launch():
        course_context = message_launch_data\
            .get('https://purl.imsglobal.org/spec/lti/claim/context', {})
        # create a deep link
        course_title = course_context.get('title', None)
        title = message_launch_data\
            .get('https://purl.imsglobal.org/spec/lti-dl/claim/deep_linking_settings', {})\
            .get('title', course_title)
        title = "Draw Together" + (f" – {title}" if title else "")

        room, _ = ExcalidrawRoom.objects.get_or_create(
            room_name=room_name,
            room_created_by=user,
            room_consumer=lti_tool,
            room_course_id=course_context.get('id', None))
        room.save()

        resource = DeepLinkResource()
        resource.set_url(absolute_reverse(request, 'lti:launch'))\
            .set_custom_params({'room': room_name})\
            .set_title(title)

        html = message_launch.get_deep_link().output_response_form([resource])
        return HttpResponse(html)

    if message_launch.is_data_privacy_launch():
        # TODO: implement data privacy screen. (not as urgent. moodle does not support this anyway.)
        raise NotImplementedError()

    if message_launch.is_resource_launch():
        # join the room
        return redirect(room_uri)

    return HttpResponseBadRequest('Unknown or unsupported message type provided.')

lti_launch.csrf_exempt = True
lti_launch.xframe_options_exempt = True
# The launch can only be triggered with a valid JWT issued by a registered platform.
