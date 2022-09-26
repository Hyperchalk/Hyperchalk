import base64
import json
import re
from typing import Any, Dict
from urllib.parse import urlparse

from asgiref.sync import sync_to_async
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.http import HttpRequest
from django.templatetags.static import static
from django.utils.translation import gettext as _
from pylti1p3.contrib.django.lti1p3_tool_config import DjangoDbToolConf
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool, LtiToolKey

from draw.utils import absolute_reverse, make_room_name

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
        'logo_uri': request.build_absolute_uri(static('ltiapi/fav-48.png'))
    }

def get_launch_url(request: HttpRequest):
    """
    Method code from https://github.com/dmitry-viskov/pylti1.3-django-example.git
    """
    target_link_uri = request.POST.get('target_link_uri', request.GET.get('target_link_uri', None))
    if not target_link_uri:
        raise Exception('Missing "target_link_uri" param')
    return target_link_uri


user_transform = re.compile(r'[^\w@.+-]')
def issuer_namespaced_username(issuer, username):
    issuer_host = user_transform.sub('_', urlparse(issuer).hostname)
    username = user_transform.sub('_', username)
    return username + '@' + issuer_host
# XXX: is there a possibility that multiple issuers reside at the same subdomain?

CLAIM = 'https://purl.imsglobal.org/spec/lti/claim'

def get_course_context(message_launch_data: dict):
    return message_launch_data\
        .get(f'{CLAIM}/context', {})

def get_custom_launch_data(message_launch_data: dict):
    return message_launch_data\
        .get(f'{CLAIM}/custom', {})

def get_ext_data(message_launch_data: dict):
    return message_launch_data\
        .get(f'{CLAIM}/ext', {})

ROLE_START = "http://purl.imsglobal.org/vocab/lis/v2/"
INSTRUCTOR_ROLE = "membership#Instructor"
SYS_ADMIN_ROLE = "system/person#Administrator"
INSTITUTION_ADMIN_ROLE = "institution/person#Administrator"
SUPERIOR_ROLES = [INSTRUCTOR_ROLE, SYS_ADMIN_ROLE, INSTITUTION_ADMIN_ROLE]

def get_roles(message_launch_data: dict):
    return [role[len(ROLE_START):] for role in message_launch_data.get(f'{CLAIM}/roles', [])]

def launched_by_superior(message_launch_data: dict):
    launch_data_roles = get_roles(message_launch_data)
    return any(role in launch_data_roles for role in SUPERIOR_ROLES)

def get_mode(message_launch_data: dict):
    return get_custom_launch_data(message_launch_data).get('mode', 'classroom')

def get_room_name(request: HttpRequest, message_launch_data: dict):
    return get_custom_launch_data(message_launch_data)\
        .get('room', None) \
        or request.GET.get('room')

def get_lti_tool(tool_conf: DjangoDbToolConf, message_launch_data: dict):
    return tool_conf.get_lti_tool(message_launch_data['iss'], message_launch_data['aud'])

def get_course_id(message_launch_data: dict):
    return get_course_context(message_launch_data).get('id', None)

def get_legacy_user_room_name(room_prefix: str, user: m.CustomUser):
    return room_prefix + base64.b64encode(user.id.bytes, altchars=b'_-').decode('ascii')[:8]

def get_user_from_launch_data(message_launch_data: dict, lti_tool: LtiTool):
    # log the user in. if this is the user's first visit, save them to the database before.
    # 1) extract user information from the data passed by the consumer
    username = get_ext_data(message_launch_data).get('user_username') # type: ignore
    username = issuer_namespaced_username(message_launch_data['iss'], username)
    user_full_name = message_launch_data.get('name', '')

    # 2) get / create the user from the db so they can be logged in
    user, __ = m.CustomUser.objects.get_or_create(
        username=username, defaults={
        'first_name': user_full_name,
        'registered_via': lti_tool})
    if user.registered_via_id != lti_tool.pk:
        # needed if tool was re-registered. otherwise trying
        # to save the user would raise an IngrityError.
        user.registered_via = lti_tool
        user.save()

    return user
