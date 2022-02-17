from django.template import Library
from draw import urls_ws

register = Library()

@register.simple_tag
def ws_url(location, *args, **kwargs):
    ...
    # TODO: custom reverse for nested URLRouters
