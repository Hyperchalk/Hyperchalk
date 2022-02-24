from typing import Optional
from urllib.parse import urlunsplit

from django.conf import settings


def build_absolute_uri_without_request(
    url: str, query: str = '', host: str = settings.LINK_BASE,
    protocol: Optional[str] = 'https'
):
    """
    Gives the absolute URI of a resource after reversing.

    ``request.build_absolute_uri()`` should be used for this usually, but somtimes the
    ``request`` is not available.

    :param url: a site-relative url

    :param query: the url query string. Defaults to an empty string.

    :param host: the current host. defaults to ``settings.LINK_BASE``.

    :param protocol: you can specify a protocol (``http(s)``) here. Defaults to ``https``.
    """
    return urlunsplit((protocol, host, url, query, None))
