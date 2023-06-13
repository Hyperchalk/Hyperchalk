"""
Local settings can be defined here. For local development, this file can simply be copied
to ``local_settings.py``. However, here is a _WARNING_: this file SHOULD be adapted for
production uses. Otherwise there _WILL_ be security issues within the app.

The settings are explained in https://docs.djangoproject.com/en/3.2/topics/settings/

You should also have a look at https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/
"""
# pylint: disable=wildcard-import,unused-wildcard-import
from draw.settings import *
from draw.utils import deepmerge

# TODO: important persons to the project. Those who get the mails when critical events happen.

# ADMINS = [('John Doe', 'doe@example.com')]
# MANAGERS = ADMINS

# allow the creation of rooms when the user visits the index page
# without specifying a room in the URL. (default is false.)
# ALLOW_AUTOMATIC_ROOM_CREATION = True

# Allow users to create custom room when they visit the index page (default is false.)
# SHOW_CREATE_ROOM_PAGE = False

# Link to an imprint page. If set, a link to this page will be
# displayed at the bottom of the index page. (default is None)
IMPRINT_URL = None

# If set to false (default), users will need to be logged in.
# ALLOW_ANONYMOUS_VISITS = True

# These rooms are accessible without any authentication or authorization. List of room names.
# PUBLIC_ROOMS = []

# Set if tracking is enabled or disabled by default. Defaults to True.
# Tracking can be enabled or disabled individually for every room. Old rooms
# from before when this setting was available will have tracking enabled.
# ENABLE_TRACKING_BY_DEFAULT = True

# TODO: uncomment this if you are going to use SQLite. Otherwise you can delete it.
# DATA_DIR = BASE_DIR / 'data'

# Should NEVER be true in production! Set to True for debug messages if you encounter an error.
DEBUG = False

# set to true if you want to serve static files. we only recommend this if you want to try out
# Hyperchalk. For any serious installation, you shold serve the static files in BASE_DIR/static_copy
# and BASE_DIR/media using a real webserver like Nginx, Apache or Caddy.
SERVE_FILES = False

# TODO: Change this and uncomment! You can get a good key by executing the following command:
# < /dev/urandom tr -dc 'A-Za-z0-9!#$%&()*+,-./:;<=>?@[\]^_`{|}~' | head -c64; echo
# the result won't include the quote-characters so you can safely put the output string in quotes

# SECRET_KEY = "super_secret_key_that_has_to_be_changed_in_production!!!"

# TODO: add your host name(s) here!

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# When you register an LTI consumer, you can call the command './manage.py makeconsumerlink'.
# This command will display a URL to you that can be used to automatically configure this app
# via the LTI Advantage registration protocol in consumers that support it. To be able to do
# this, you have to configure your host name here, which will be used to generate said link.
# The LINK_BASE will also be added to the list of CSRF_TRUSTED_ORIGINS as "https://LINK_BASE".
#
# TODO: uncomment this and enter your host name.

# LINK_BASE = 'localhost:8000'

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases
#
# The first example is an sqlite database in the BASE_PATH. PostgreSQL and
# MySQL / MariaDB are also supported. Have a look at the link above to see
# how to configure this to integrate with your database.
#
# WARNING: do not use sqlite with more than one thread / process!
#
# TODO: uncommment this and enter your database settings here.

# DATABASES = {
#     # uncomment this if you want SQLite
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME':   DATA_DIR / 'db.sqlite3',
#     },
#     # uncomment this if you want MySQL / Postgres
#     'default': {
#         'ENGINE':   'django.db.backends.mysql',       # uncomment for mysql
#         'ENGINE':   'django.db.backends.postgresql',  # uncomment for postgres
#         'HOST':     'TODO', # db host. name of your docker service if you connect a db via docker.
#         'NAME':     'TODO', # name of your database
#         'USER':     'TODO',
#         'PASSWORD': 'TODO',
#     },
# }

# Caching
# https://docs.djangoproject.com/en/4.0/topics/cache/
#
# By default, Django will use the in-Memory cache. As the LTI lib will use the cache to look up the
# LTI nonce over multiple requests on tool configuration, the cache needs to be the same for all
# worker processes. This cannot be achieved via the in-memory caching-mechanism. If you use redis
# anyway as the channels backend, you may want to just use it for caching, too.
#
# TODO: uncomment to configure caching. required if you want to run more than one worker process.

# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         # 6379 is the default redis port. if you use docker, the hostname is the name of
#         # the redis service. if you have a redis cluster, just add all servers to the list,
#         # beginning with the leader. the url scheme is: 'redis://username:password@host:port'
#         # or 'redis://host:port' if authentication is disabled on your redis.
#         'LOCATION': ['redis://redis:6379']
#     }
# }

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
#
# TODO: uncomment this and configure your desired channel layer

# CHANNEL_LAYERS = {
#     # uncomment this if you only run one worker process
#     "default": {
#         "BACKEND": "channels.layers.InMemoryChannelLayer",
#     },
#     # uncomment this if you have more than one worker process and use redis
#     "default": {
#         "BACKEND": "channels_redis.core.RedisChannelLayer",
#         "CONFIG": {
#             # schema of this tuple is (hostname, port). if you use
#             # docker, the hostname is the name of your service.
#             "hosts": [("redis", 6379)],
#         },
#     },
# }

# Logging
# https://docs.djangoproject.com/en/3.2/topics/logging/
#
# TODO: if you need some custom logging, you can configre it here.

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
#
# TODO: configure mail

# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = ...
# EMAIL_PORT = 587
# EMAIL_HOST_USER = ...
# EMAIL_HOST_PASSWORD = ...
# EMAIL_USE_TLS = True
# EMAIL_USE_SSL = False                     # mutually exclusive to EMAIL_USE_TLS
# EMAIL_SUBJECT_PREFIX = '[Hyperchalk]'

# Static files
# https://docs.djangoproject.com/en/3.2/ref/contrib/staticfiles/
#
# usually, you don't need to change this.
#
# TODO: if you want to serve some custom static files, configure them here.

# STATICFILES_DIRS.append(BASE_DIR / 'tmp')

# Time Zones
# https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
#
# TODO: configure your time zone.

TIME_ZONE = 'CET'

# NOTE: IMPORTANT. DO NOT REMOVE.
finalize_settings(locals())
