# pylint: disable=wildcard-import,unused-wildcard-import
try:
    from local_settings import *

except ModuleNotFoundError:
    # provide minimal testing setup
    import json
    import os

    from draw.settings import *

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        },
        **json.loads(os.environ.get('DJANGO_DATABASES', '{}'))
    }
    SECRET_KEY = "super_secret_key_that_has_to_be_changed_in_production!!!"
    TIME_ZONE = "UTC"
    LINK_BASE = 'localhost:8000'

    finalize_settings(locals())
