from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
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
            json_link = reverse('collab:record-json', kwargs={
                'room_name': obj.room_name, 'pk': obj.pk
            })
            return format_html(
                "<a href={json_link}>{text}</a>",
                json_link=json_link, text=_("Go to JSON"))
        return _('will be generated after saving')


@admin.register(m.ExcalidrawRoom)
class ExcalidrawRoomAdmin(admin.ModelAdmin):
    readonly_fields = ['room_json', 'replay_link']

    @admin.display(description=_("View Room in Browser JSON Viewer"))
    def room_json(self, obj: m.ExcalidrawRoom):
        if obj.pk:
            room_link = reverse('collab:room-json', kwargs={'room_name': obj.room_name})
            return format_html(
                "<a href='{room_link}'>{text}</a>",
                room_link=room_link,
                text=_('Go to room JSON'))
        return _('will be generated after saving')

    @admin.display(description=_("Replay Mode"))
    def replay_link(self, obj: m.ExcalidrawRoom):
        if obj.pk:
            room_link = reverse('collab:replay-room', kwargs={'room_name': obj.room_name})
            return format_html(
                "<a href='{room_link}'>{text}</a>",
                room_link=room_link, text=_("Replay this room"))
        return _('will be generated after saving')
