import asyncio
import logging
import re
from pprint import pformat
from typing import List, Optional
from urllib.parse import urlparse

import aiohttp
from asgiref.sync import sync_to_async
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.utils.decorators import classonlymethod
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import DetailView
from pylti1p3.contrib.django import DjangoCacheDataStorage, DjangoMessageLaunch, DjangoOIDCLogin
from pylti1p3.contrib.django.lti1p3_tool_config import DjangoDbToolConf

from django.utils.functional import lazy

from . import models as m
from .utils import lti_registration_data, make_tool_config_from_openid_config_via_link

logger = logging.getLogger("ltiapi")


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

    # pylint: disable=invalid-overridden-method
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


async def oidc_jwks(request: HttpRequest, issuer: Optional[str] = None, client_id: Optional[str] = None):
    tool_conf = DjangoDbToolConf()
    return JsonResponse(tool_conf.get_jwks(issuer, client_id))

# TODO: implement endpoints for lauch, deeplink configuration and drawing board
# TODO: implement the routes that are needed for the request data


def get_launch_url(request: HttpRequest):
    """
    Method code from https://github.com/dmitry-viskov/pylti1.3-django-example.git
    """
    target_link_uri = request.POST.get('target_link_uri', request.GET.get('target_link_uri', None))
    if not target_link_uri:
        raise Exception('Missing "target_link_uri" param')
    return target_link_uri


def oidc_login(request: HttpRequest):
    tool_conf = DjangoDbToolConf()
    launch_data_storage = DjangoCacheDataStorage()

    oidc_login = DjangoOIDCLogin(request, tool_conf, launch_data_storage=launch_data_storage)
    target_link_uri = get_launch_url(request)
    redirect = oidc_login\
        .enable_check_cookies()\
        .redirect(target_link_uri, False)
    return redirect

oidc_login.csrf_exempt = True
# XXX: what caould go wrong if an attacker would trigger the login
#      for a known issuer? could they somehow change a deeplink?
# YYY: → is the OIDC login flow csrf-safe? there is no possibility
#      to pass a valid csrf token by the LTI Platform though...
# TODO: it would be nice to have the referrer check logic from the
#       csrf middleware here so at least this could be checked.

user_transform = re.compile(r'[^\w@.+-]')
def issuer_namespaced_username(issuer, username):
    issuer_host = user_transform.sub('_', urlparse(issuer).hostname)
    username = user_transform.sub('_', username)
    return username + '@' + issuer_host
# XXX: is there a possibility that multiple issuers reside at the same subdomain?

lazy_pformat = lazy(pformat, str)

@require_POST
def lti_launch(request: HttpRequest):
    tool_conf = DjangoDbToolConf()
    launch_data_storage = DjangoCacheDataStorage()
    message_launch = DjangoMessageLaunch(request, tool_conf, launch_data_storage=launch_data_storage)
    message_launch_data = message_launch.get_launch_data()
    # lazy_pformat: only format the data if it will be logged.
    logger.debug("launch with data:\n%s", lazy_pformat(message_launch_data))

    username = message_launch_data['https://purl.imsglobal.org/spec/lti/claim/ext']['user_username']
    issuer = message_launch_data['iss']
    username = issuer_namespaced_username(issuer, username)

    # TODO: get or create the user

    if message_launch.is_deep_link_launch():
        # TODO: implement deep link config
        return ...

    if message_launch.is_data_privacy_launch():
        # TODO: implement data privacy screen
        return ...

    if message_launch.is_resource_launch():
        # TODO: implement resource
        return ...

    return render(request, 'game.html', {
        'page_title': PAGE_TITLE,
        'is_deep_link_launch': message_launch.is_deep_link_launch(),
        'launch_data': message_launch.get_launch_data(),
        'launch_id': message_launch.get_launch_id(),
        'curr_user_name': message_launch_data.get('name', ''),
        'curr_diff': difficulty
    })

lti_launch.csrf_exempt = True
# The launch can only be triggered with a valid JWT issued by a registered platform.
