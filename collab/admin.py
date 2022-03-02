from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from . import models as m


@admin.register(m.ExcalidrawLogRecord)
class ExcalidrawLogRecordAdmin(admin.ModelAdmin):
    list_display = ["__str__", "room_name", "event_type"]
    fields = [
        "room_name",
        "event_type",
        "user_pseudonym",
        ("_compressed", "compressed_size", "uncompressed_size", "compression_degree"),
        "view_json",
        "created_at",
    ]
    readonly_fields = [
        "content", "_compressed", "compressed_size", "view_json",
        "compression_degree", "uncompressed_size", "created_at"]

    @admin.display(description="View Room in Browser JSON Viewer")
    def view_json(self, obj: m.ExcalidrawLogRecord):
        if obj.pk:
            json_link = reverse('collab:record', kwargs={'pk': obj.pk})
            return mark_safe(f"<a href={json_link}>Go to JSON</a>")
        return _('will be generated after saving')


@admin.register(m.ExcalidrawRoom)
class ExcalidrawRoomAdmin(admin.ModelAdmin):
    readonly_fields = ['room_json']

    @admin.display(description="View Room in Browser JSON Viewer")
    def room_json(self, obj: m.ExcalidrawRoom):
        if obj.pk:
            room_link = reverse('collab:room', kwargs={'room_name': obj.room_name})
            return mark_safe(f"<a href='{room_link}'>Go to room JSON</a>")
        return _('will be generated after saving')
