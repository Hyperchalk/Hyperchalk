from importlib import import_module

from channels.routing import URLRouter


def ws_include(routing_config):
    routing = import_module(routing_config)
    return URLRouter(routing.urlpatterns)
