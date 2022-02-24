"""
Django settings for draw project.

Generated by 'django-admin startproject' using Django 3.2.12.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from pathlib import Path
from typing import Any, Dict, Iterable, List, Union
from urllib.parse import urlparse

from django.utils.module_loading import import_string

from draw.utils import StrLike

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS: List[str] = ['localhost', '127.0.0.1']

INTERNAL_IPS = ['127.0.0.1']

# Configure https reverse proxy
# https://docs.djangoproject.com/en/4.0/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Application definition

INSTALLED_APPS = [
    'collab',
    'ltiapi',
    'pylti1p3.contrib.django.lti1p3_tool_config',
    # 'debug_toolbar',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels'
]

MIDDLEWARE = [
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

WS_MIDDLEWARE = [
    'channels.security.websocket.AllowedHostsOriginValidator',
    'channels.auth.AuthMiddlewareStack'
]

ROOT_URLCONF = 'draw.urls'
CHANNELS_URLCONF = 'draw.urls_ws'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'draw.wsgi.application'
ASGI_APPLICATION = 'draw.asgi.application'

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES: Dict[str, Dict[str, Union[StrLike, Dict[str, StrLike]]]] = {}

# Channel Layers
# https://channels.readthedocs.io/en/latest/topics/channel_layers.html
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# https://docs.djangoproject.com/en/3.2/topics/auth/customizing/#auth-custom-user
AUTH_USER_MODEL = 'ltiapi.CustomUser'

# https://docs.djangoproject.com/en/3.2/ref/settings/#csrf-trusted-origins
class TrustedOrigins(Iterable[str]):
    """
    Iterable of trusted origins for embedding this application in iframes.

    The allowed origins should be the tools configured from the database. But since the settings
    are loaded before the database, additional settings can't be pulled from the db at this point.
    The CSRF middleware casts ``CSRF_TRUSTED_ORIGINS`` this to a ``list`` when it runs. So the
    model will be loaded precisely at this point. The allowed hosts are then the hostnames of the
    issuer field of the :model:`lti1p3_tool_config.LtiTool` configs (speak the LTI platforms).
    """
    def __init__(self) -> None:
        self.tool_model = None

    def __iter__(self):
        if not self.tool_model:
            lti_path = 'pylti1p3.contrib.django.lti1p3_tool_config.models.LtiTool'
            self.tool_model = import_string(lti_path)
        for (issuer,) in self.tool_model.objects.all().values_list('issuer'):
            print(f'csrf check issuer: {issuer}/')
            yield urlparse(issuer).hostname

CSRF_TRUSTED_ORIGINS = iter(TrustedOrigins())

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'de-DE'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'static_copy'

STATICFILES_DIRS = [
    BASE_DIR / 'client' / 'dist',
]

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

# DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Settings for LTI ToolConfig
# see lti.tool_config.py

LTI_CONFIG = {
    'title': 'Excalidraw',
    'description': 'The Excalidraw drawing board app as an LTI module.',
    'vendor_name': 'EduTec@DIPF',
    'vendor_url': 'https://www.edutec.science/',
    'vendor_contact_name': 'Praktikant:in',
    'vendor_contact_email': 'praktikum_alice@dipf.de',
}

# call this from your custom settings
def finalize_settings(final_locals: Dict[str, Any]):
    required_vars = {'SECRET_KEY', 'DATABASES', 'TIME_ZONE', 'LINK_BASE'}
    missing = required_vars.difference(final_locals.keys())
    if missing:
        raise ValueError(f'The following mandatory keys are missing from your config: {missing}')
