import asyncio
import logging
from typing import Optional

import aiohttp
from asgiref.sync import sync_to_async
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import classonlymethod
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
        # configuration flow documented at https://moodlelti.theedtech.dev/dynreg/
        openid_config_endpoint = request.GET.get('openid_configuration')
        jwt_str = request.GET.get('registration_token')

        async with aiohttp.ClientSession() as session:
            logger.info('Getting registration data from "%s"', openid_config_endpoint)
            resp = await session.get(openid_config_endpoint)
            openid_config = await resp.json()

            tool_provider_registration_endpoint = openid_config['registration_endpoint']
            logger.info('Registering tool at "%s"', tool_provider_registration_endpoint)
            # TODO: implement the routes that are needed for the request data
            resp = await session.post(
                tool_provider_registration_endpoint,
                data=lti_registration_data(request),
                headers={'Authorization': 'Bearer ' + jwt_str})
            openid_registration = await resp.json()

        reg_link: m.OneOffRegistrationLink = await sync_to_async(self.get_object)() # type: ignore
        try:
            consumer = await make_tool_config_from_openid_config_via_link(
                openid_config, openid_registration, reg_link)
        except AssertionError as e:
            ctx = self.get_context_data(registration_success=False, error=e)
            return self.render_to_response(ctx, status=406)

        reg_link.registration_complete(consumer)

        logging.info(
            'Registration of issuer "%s" with client %s complete',
            consumer.issuer, consumer.client_id)
        ctx = self.get_context_data(registration_success=True)
        return self.render_to_response(ctx)

async def get_jwks(request, issuer: Optional[str] = None, client_id: Optional[str] = None):
    tool_conf = DjangoDbToolConf()
    return JsonResponse(tool_conf.get_jwks(issuer, client_id))

# TODO: implement endpoints for lauch, deeplink configuration and drawing board
