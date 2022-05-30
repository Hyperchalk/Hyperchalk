from django.apps import AppConfig
from django.conf import settings
from django.core.signals import request_started
from django.utils.module_loading import import_string

from draw.utils import TrustedOrigins


class LtiapiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ltiapi'

    def ready(self) -> None:
        if isinstance(settings.CSRF_TRUSTED_ORIGINS, TrustedOrigins):
            def request_start_handler(sender, **kwargs):
                Tool = import_string('pylti1p3.contrib.django.lti1p3_tool_config.models.LtiTool')
                settings.CSRF_TRUSTED_ORIGINS.connected(Tool)
                settings.CSRF_TRUSTED_ORIGINS\
                    .update_issuers(additional_issuers=[f'https://{settings.LINK_BASE}'])
            request_started.connect(request_start_handler)
        return super().ready()
