"""
Local settings can be defined here.

The settings are explained in https://docs.djangoproject.com/en/3.2/topics/settings/

You should also have a look at https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/
"""
# pylint: disable=wildcard-import,unused-wildcard-import
from os import environ as env

import dj_database_url

from draw.settings import *
from draw.utils import deepmerge

# important persons to the project. Those who get the mails when critical events happen.

ADMINS = [(env.get("HC_ADMIN_NAME"), env.get("HC_ADMIN_MAIL"))]
MANAGERS = ADMINS

# allow the creation of rooms when the user visits the index page
# without specifying a room in the URL. (default is false.)
ALLOW_AUTOMATIC_ROOM_CREATION = env.get("HC_ALLOW_AUTOMATIC_ROOM_CREATION") == "true"

# Allow users to create custom room when they visit the index page (default is false.)
SHOW_CREATE_ROOM_PAGE = env.get("HC_SHOW_CREATE_ROOM_PAGE") == "true"

# Link to an imprint page. If set, a link to this page will be
# displayed at the bottom of the index page. (default is None)
IMPRINT_URL = env.get("HC_IMPRINT_URL", None)

# If set to false (default), users will need to be logged in.
ALLOW_ANONYMOUS_VISITS = env.get("HC_ALLOW_ANONYMOUS_VISITS") == "true"

# These rooms are accessible without any authentication or authorization. List of room names.
PUBLIC_ROOMS = env.get("HC_PUBLIC_ROOMS", "").split(",")

# Set if tracking is enabled or disabled by default. Defaults to True.
# Tracking can be enabled or disabled individually for every room. Old rooms
# from before when this setting was available will have tracking enabled.
ENABLE_TRACKING_BY_DEFAULT = env.get("HC_ENABLE_TRACKING_BY_DEFAULT") != "false"
ENABLE_TRACKING_BY_DEFAULT_FOR_LTI = env.get("HC_ENABLE_TRACKING_BY_DEFAULT_FOR_LTI") != "false"

# Should NEVER be true in production! Set to True for debug messages if you encounter an error.
DEBUG = env.get("HC_DEBUG") == "true"

# set to true if you want to serve static files. we only recommend this if you want to try out
# Hyperchalk. For any serious installation, you shold serve the static files in BASE_DIR/static_copy
# and BASE_DIR/media using a real webserver like Nginx, Apache or Caddy.
SERVE_FILES = env.get("HC_SERVE_FILES") == "true"

# You can get a good key by executing the following command:
# < /dev/urandom tr -dc 'A-Za-z0-9!#$%&()*+,-./:;<=>?@[\]^_`{|}~' | head -c64; echo
# the result won't include the quote-characters so you can safely put the output string in quotes

SECRET_KEY = env.get("HC_SECRET_KEY")
if not SECRET_KEY:
    raise KeyError("No HC_SECRET_KEY provided")

ALLOWED_HOSTS = env.get("HC_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# When you register an LTI consumer, you can call the command './manage.py makeconsumerlink'.
# This command will display a URL to you that can be used to automatically configure this app
# via the LTI Advantage registration protocol in consumers that support it. To be able to do
# this, you have to configure your host name here, which will be used to generate said link.
# The LINK_BASE will also be added to the list of CSRF_TRUSTED_ORIGINS as "https://LINK_BASE".

LINK_BASE = env.get("HC_LINK_BASE")

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases
#
# The first example is an sqlite database in the BASE_PATH. PostgreSQL and
# MySQL / MariaDB are also supported. Have a look at the link above to see
# how to configure this to integrate with your database.
#
# WARNING: do not use sqlite with more than one thread / process!

# NOTE: the environment variable where this gets its config from is called "DATABASE_URL"
DATA_DIR = BASE_DIR / 'data'
DATABASES = {
    'default': dj_database_url.config(default=f'sqlite:///{DATA_DIR / "db.sqlite3"}'),
}

# Caching
# https://docs.djangoproject.com/en/4.0/topics/cache/
#
# By default, Django will use the in-Memory cache. As the LTI lib will use the cache to look up the
# LTI nonce over multiple requests on tool configuration, the cache needs to be the same for all
# worker processes. This cannot be achieved via the in-memory caching-mechanism. If you use redis
# anyway as the channels backend, you may want to just use it for caching, too.

DEFAULT_REDIS = "redis://redis:6379"

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        # 6379 is the default redis port. if you use docker, the hostname is the name of
        # the redis service. if you have a redis cluster, just add all servers to the list,
        # beginning with the leader. the url scheme is: 'redis://username:password@host:port'
        # or 'redis://host:port' if authentication is disabled on your redis.
        'LOCATION': env.get("HC_REDIS_URL", DEFAULT_REDIS).split(",")
    }
}

# Channel Layers
# https://channels.readthedocs.io/en/latest/topics/channel_layers.html
#
# Channels layers are the layer which the websocket interface uses to communicate between different
# websocket connections. By default, this uses the in memory layer. This should however not be used
# in production, as it does not allow communication between threads and processes. If you plan to
# run the app with only one thread in one process, this is fine. Otherwise it could happen that the
# clients trying to connect to the same room land in different threads, which would lead to the same
# room being created twice with diverging local copies and either of the copies being saved to the
# room table alternatingly.
#
# To prevent this from happening, use either the Redis layer [1][2], the layers implementation for
# postgres [2] or any other layers implementation that suits your needs.
#
# [1]: https://channels.readthedocs.io/en/stable/topics/channel_layers.html#redis-channel-layer
# [2]: https://pypi.org/project/channels-redis/
# [3]: https://github.com/danidee10/channels_postgres/

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": env.get("HC_REDIS_URL", DEFAULT_REDIS).split(","),
        },
    },
}

# Logging
# https://docs.djangoproject.com/en/3.2/topics/logging/

LOGGING = deepmerge(LOGGING, {
    'handlers': {
        'draw_logging': {
            'level': 'WARNING',
            # 'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        }
    },
    'loggers': {
        'draw': {
            'level': 'WARNING',
            'handlers': ['draw_logging'],
        },
    }
})

# Email
# https://docs.djangoproject.com/en/3.2/ref/settings/#email-backend
# https://docs.djangoproject.com/en/3.2/topics/email/
#
# Though this application does not send custom mails (yet), you might be interested in configuring
# mail, so get admin-mailed when critical events get logged.

if env.get("HC_EMAIL_BACKEND"):
    EMAIL_BACKEND = env.get("HC_EMAIL_BACKEND")
if env.get("HC_EMAIL_HOST"):
    EMAIL_BACKEND = env.get("HC_EMAIL_BACKEND", 'django.core.mail.backends.smtp.EmailBackend')
    EMAIL_HOST = env.get("HC_EMAIL_HOST")
    EMAIL_PORT = int(env.get("HC_EMAIL_PORT", "465"))
    EMAIL_HOST_USER = env.get("HC_EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = env.get("HC_EMAIL_HOST_PASSWORD")
    EMAIL_USE_TLS = env.get("HC_EMAIL_USE_TLS", "true") == "true"
    EMAIL_USE_SSL = env.get("HC_EMAIL_USE_SSL", "false") == "true" # mutually exclusive to EMAIL_USE_TLS
if env.get("HC_EMAIL_HOST") or env.get("HC_EMAIL_BACKEND"):
    EMAIL_SUBJECT_PREFIX = env.get("HC_EMAIL_SUBJECT_PREFIX", '[Hyperchalk]')

# Time Zones
# https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

TIME_ZONE = env.get("HC_TIME_ZONE", 'CET')

# Language settings
# The language code is respected by django, as well as excalidraw
# https://docs.djangoproject.com/en/4.1/ref/settings/#language-code

LANGUAGE_CODE = env.get("HC_LANGUAGE_CODE", "en-US")

# NOTE: IMPORTANT. DO NOT REMOVE.
finalize_settings(locals())
