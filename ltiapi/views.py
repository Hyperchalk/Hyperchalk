from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.templatetags.static import static
from django.urls import reverse
from lti import ToolConfig


async def lti_config(request: HttpRequest, *args, **kwargs):
    # basic view code from https://pypi.org/project/lti/
    # basic stuff
    referrer = request.META.get('HTTP_REFERER', None)
    if referrer and referrer not in settings.ALLOWED_LTI_HOSTS:
        raise PermissionDenied(
            "This Host is not an allowed LTI host. You may ask "
            "an admin to change ALLOWED_LTI_CONSUMERS accordingly")
    launch_view_name = 'lti:launch'
    launch_url = request.build_absolute_uri(reverse(launch_view_name))
    icon_url = request.build_absolute_uri(static('ltiapi/fav.gif'))

    # maybe you've got some extensions
    # extensions = {
    #     'my_extensions_provider': {
    #         # extension settings...
    #     }
    # }

    lti_tool_config = ToolConfig(
        **settings.LTI_CONFIG,
        launch_url=launch_url,
        secure_launch_url=launch_url,
        # extensions=extensions,
        icon=icon_url,
        cartridge_bundle='BLTI001_Bundle',
        cartridge_icon='BLTI001_Icon',
    )

    return HttpResponse(lti_tool_config.to_xml(), content_type='text/xml')

async def lti_launch(request: HttpRequest, *args, **kwargs):
    return HttpResponse()
