import json
from typing import Any, Dict

from asgiref.sync import sync_to_async
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.http import HttpRequest
from django.templatetags.static import static
from django.utils.translation import gettext as _
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool, LtiToolKey

from draw.utils import absolute_reverse

from . import models as m


async def generate_key_pair(key_size=4096):
    """
    Generates an RSA key pair. Async because generating a key can be resource intensive.

    :param key_size: key bits

    :returns: a dict with the keys "public" and "private", containing PEM-encoded RSA keys. \
        This is not returned as a tuple so that the user of this function never confuses them.
    """
    generate_private_key = sync_to_async(rsa.generate_private_key, thread_sensitive=False)
    private_key = await generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )
    public_key = private_key.public_key()

    private_key_str = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()

    public_key_str = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()

    return {'private': private_key_str, 'public': public_key_str}

async def keys_for_issuer(issuer_name: str) -> LtiToolKey:
    get_or_create_key = sync_to_async(LtiToolKey.objects.get_or_create)
    key_obj, created = await get_or_create_key(name=issuer_name)
    if created:
        key_pair = await generate_key_pair()
        key_obj.private_key = key_pair['private']
        key_obj.public_key = key_pair['public']
        await sync_to_async(key_obj.save)()
    return key_obj

async def make_tool_config_from_openid_config_via_link(
    openid_config: Dict[str, Any],
    openid_registration: Dict[str, Any],
    one_off_registration: m.OneOffRegistrationLink
):
    conf_spec = "https://purl.imsglobal.org/spec/lti-platform-configuration"
    assert conf_spec in openid_config, \
        "The OpenID config is not an LTI platform configuration"

    tool_spec = "https://purl.imsglobal.org/spec/lti-tool-configuration"
    assert tool_spec in openid_registration, \
        "The OpenID registration is not an LTI tool configuration"

    deployment_ids = [openid_registration[tool_spec]['deployment_id']]

    consumer_config = LtiTool(
        title=one_off_registration.consumer_name,
        issuer=openid_config['issuer'],
        client_id=openid_registration['client_id'],
        auth_login_url=openid_config['authorization_endpoint'],
        auth_token_url=openid_config['token_endpoint'],
        auth_audience=openid_config['token_endpoint'],
        key_set_url=openid_config['jwks_uri'],
        tool_key=await keys_for_issuer(openid_config['issuer']),
        deployment_ids=json.dumps(deployment_ids),
    )
    await sync_to_async(consumer_config.save)() # type: ignore
    return consumer_config

def lti_registration_data(request: HttpRequest):
    return {
        'response_types': [
            'id_token'
        ],
        'application_type': 'web',
        'client_name': str(_('%s by %s') % (
            settings.LTI_CONFIG['title'],
            settings.LTI_CONFIG['vendor_name'],
        )),
        'initiate_login_uri': absolute_reverse(request, 'lti:login'),
        'grant_types': [
            'implicit',
            'client_credentials'
        ],
        'jwks_uri': absolute_reverse(request, 'lti:jwks'),
        'token_endpoint_auth_method': 'private_key_jwt',
        'redirect_uris': [
            absolute_reverse(request, 'lti:launch'),
            absolute_reverse(request, 'collab:index'),
        ],
        # https://www.imsglobal.org/spec/security/v1p0/#h_scope-naming-conventions
        'scope': ['https://purl.imsglobal.org/spec/lti-nrps/scope/contextmembership.readonly'],
        'https://purl.imsglobal.org/spec/lti-tool-configuration': {
            'domain': request.get_host(), # get_host includes the port.
            'target_link_uri': request.build_absolute_uri('/'),
            'claims': ['iss', 'sub', 'name'],
            'messages': [{
                'type': 'LtiDeepLinkingRequest',
                'target_link_uri': absolute_reverse(request, 'lti:launch'),
                'label': str(_('New drawing board')),
            }],
            'description': settings.LTI_CONFIG['description'],
        },
        'logo_uri': request.build_absolute_uri(static('ltiapi/fav.gif'))
    }
