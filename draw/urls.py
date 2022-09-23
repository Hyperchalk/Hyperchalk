"""draw URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.templatetags.static import static as static_file
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from django.views import generic

from .api import api
from .utils.auth import user_is_staff_view

admin.site.site_title = "Hyperchalk"
admin.site.site_header = _("Hyperchalk Admin Page")

urlpatterns = [
    path('lti/', include('ltiapi.urls')),
    path('admin/', admin.site.urls),
    path('is-staff/', user_is_staff_view, name='is-staff'),
    path('favicon.ico', generic.RedirectView.as_view(url=static_file('favicon.ico'))),
    path('', include('collab.urls')),
    path('api/', api.urls)
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns

if settings.DEBUG or settings.SERVE_FILES:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
