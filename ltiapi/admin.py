from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpRequest

from draw.utils import chain

from . import models as m
from .models import CustomUser

admin.site.register(CustomUser, UserAdmin)


@admin.register(m.OneOffRegistrationLink)
class OneOffRegistrationLinkAdmin(admin.ModelAdmin):
    list_display = ['consumer_name', 'id']
    readonly_fields = ['registration_link']

    # pylint: disable=signature-differs,attribute-defined-outside-init

    def get_readonly_fields(self, request: HttpRequest, obj: m.OneOffRegistrationLink):
        if not chain(obj, ('pk',)):
            return []
        return super().get_readonly_fields(request, obj)

    def changeform_view(self, request, *args, **kwargs):
        self.request = request
        return super().changeform_view(request, *args, **kwargs)

    @admin.display(description="One off registration link")
    def registration_link(self, obj: m.OneOffRegistrationLink):
        return obj.get_uri(self.request)
