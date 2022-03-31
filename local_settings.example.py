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

# TODO: uncomment this if you are going to use SQLite. Otherwise you can delete it.
# DATA_DIR = BASE_DIR / 'data'

# Should NEVER be true in production!
DEBUG = False

# TODO: Change this and uncomment! You can get a good key by executing the following command:
# < /dev/urandom tr -dc 'A-Za-z0-9!#$%&()*+,-./:;<=>?@[\]^_`{|}~' | head -c64; echo
# the result won't include the quote-characters so you can safely put the output string in quotes

# SECRET_KEY = "super_secret_key_that_has_to_be_changed_in_production!!!"

# TODO: uncomment and add your host name(s) here!

# ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# When you register an LTI consumer, you can call the command './manage.py makeconsumerlink'.
# This command will display a URL to you that can be used to automatically configure this app
# via the LTI Advantage registration protocol in consumers that support it. To be able to do
# this, you have to configure your host name here, which will be used to generate said link.
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
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME':   DATA_DIR / 'db.sqlite3',
#     },
#     'default': {
#         'ENGINE':   'django.db.backends.mysql',
#         'NAME':     'TODO',
#         'HOST':     'TODO',
#         'PASSWORD': 'TODO',
#     },
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
# To prevent this from happening, use either the Redis layer [1], the layers implementation for
# postgres [2] or any other layers implementation that suits your needs.
#
# [1]: https://channels.readthedocs.io/en/stable/topics/channel_layers.html#redis-channel-layer
# [2]: https://github.com/danidee10/channels_postgres/
#
# TODO: uncomment this and configure your desired channel layer

# CHANNEL_LAYERS = {
#     "default": {
#         "BACKEND": "channels.layers.InMemoryChannelLayer",
#     },
#     "default": {
#         "BACKEND": "channels_redis.core.RedisChannelLayer",
#         "CONFIG": {
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
# EMAIL_SUBJECT_PREFIX = '[LTI DrawApp]'

# Static files
# https://docs.djangoproject.com/en/3.2/ref/contrib/staticfiles/
#
# TODO: if you want to serve some custom static files, configure them here.

# STATICFILES_DIRS.append(BASE_DIR / 'tmp')

# TODO: configure your time zone.

TIME_ZONE = 'CET'

# NOTE: IMPORTANT. DO NOT REMOVE.
finalize_settings(locals())
