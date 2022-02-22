import asyncio
import logging
from typing import List, Optional

import aiohttp
from asgiref.sync import sync_to_async
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import classonlymethod
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from pylti1p3.contrib.django.lti1p3_tool_config import DjangoDbToolConf

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
            # if the provider returns an error, show the error page.
            # if resp.content_type.startswith('text/html') and settings.DEBUG:
            #     return HttpResponse(await resp.read())
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

async def jwks(request, issuer: Optional[str] = None, client_id: Optional[str] = None):
    tool_conf = DjangoDbToolConf()
    return JsonResponse(tool_conf.get_jwks(issuer, client_id))

# TODO: implement endpoints for lauch, deeplink configuration and drawing board
# TODO: implement the routes that are needed for the request data

async def login(request):
    ...
    # tool_conf = get_tool_conf()
    # launch_data_storage = get_launch_data_storage()

    # oidc_login = DjangoOIDCLogin(request, tool_conf, launch_data_storage=launch_data_storage)
    # target_link_uri = get_launch_url(request)
    # return oidc_login\
    #     .enable_check_cookies()\
    #     .redirect(target_link_uri)


async def launch(request):
    ...
