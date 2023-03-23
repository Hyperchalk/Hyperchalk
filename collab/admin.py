from django.contrib import admin
from django.contrib.admin.actions import delete_selected
from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from . import models as m


@admin.register(m.ExcalidrawLogRecord)
class ExcalidrawLogRecordAdmin(admin.ModelAdmin):
    list_display = ["__str__", "room_name", "short_user_pseudonym", "event_type", "created_at"]
    fields = [
        "room_name",
        "event_type",
        ("short_user_pseudonym", "user_pseudonym"),
        ("_compressed", "compressed_size", "uncompressed_size", "compression_degree"),
        "view_json",
        "created_at",
    ]
    readonly_fields = [
        "content", "_compressed", "compressed_size", "view_json", "created_at",
        "short_user_pseudonym", "compression_degree", "uncompressed_size"]

    @admin.display(description=_("View Record in Browser JSON Viewer"))
    def view_json(self, obj: m.ExcalidrawLogRecord):
        if obj.pk:
            json_link = reverse('api-1:get_record', kwargs={
                'room_name': obj.room_name, 'pk': obj.pk
            })
            return format_html(
                "<a href={json_link} target='_blank'>{text}</a>",
                json_link=json_link, text=_("Go to JSON"))
        return _('will be generated after saving')

    @admin.display(description=_("shortened pseudonym"))
    def short_user_pseudonym(self, obj: m.ExcalidrawLogRecord):
        return obj.user and obj.user_pseudonym[:16]


@admin.register(m.ExcalidrawRoom)
class ExcalidrawRoomAdmin(admin.ModelAdmin):
    fields = [
        "room_name",
        "room_created_by",
        "tracking_enabled",
        ("created_at", "last_update"),
        ("room_consumer", "room_course_id"),
        "room_link",
        "room_json",
        "replay_link"
    ]
    readonly_fields = [
        "room_json", "replay_link", "room_link", "last_update", "created_at",
        "compressed_size", "uncompressed_size", "compression_degree"]
    list_display = ["__str__", "room_link", "compressed_size", "created_at", "last_update"]
    actions = ["discard_unused_rooms", "clone_rooms"]

    @admin.display(description=_("View Room"))
    def room_link(self, obj: m.ExcalidrawRoom):
        if obj.pk:
            room_link = reverse('collab:room', kwargs={'room_name': obj.room_name})
            return format_html(
                "<a href='{room_link}' target='_blank'>{text}</a>",
                room_link=room_link,
                text=_('Go to room'))
        return _('will be generated after saving')

    @admin.display(description=_("View Room in Browser JSON Viewer"))
    def room_json(self, obj: m.ExcalidrawRoom):
        if obj.pk:
            room_link = reverse('api-1:get_room', kwargs={'room_name': obj.room_name})
            return format_html(
                "<a href='{room_link}' target='_blank'>{text}</a>",
                room_link=room_link,
                text=_('Go to room JSON'))
        return _('will be generated after saving')

    @admin.display(description=_("Replay Mode"))
    def replay_link(self, obj: m.ExcalidrawRoom):
        if obj.pk:
            room_link = reverse('collab:replay-room', kwargs={'room_name': obj.room_name})
            return format_html(
                "<a href='{room_link}' target='_blank'>{text}</a>",
                room_link=room_link, text=_("Replay this room"))
        return _('will be generated after saving')

    @admin.display(description=_("Discard all empty rooms (ONLY USE THIS ON TEST INSTANCES)"))
    def discard_unused_rooms(self, request, queryset):
        empty_rooms = queryset.filter(_elements=m.EMPTY_JSON_LIST_ZLIB_COMPRESSED)
        return delete_selected(self, request, empty_rooms)

    @admin.display(description=_("Clone room(s)"))
    def clone_rooms(self, request, queryset):
        new_rooms = []
        for room in queryset:
            new_rooms.append(room.clone(None, request.user, room.room_consumer))
        self.message_user(
            request,
            _("Rooms created: %s") % ", ".join([r.room_name for r in new_rooms]),
            messages.SUCCESS)


@admin.register(m.Pseudonym)
class ExcalidrawPseudonymAdmin(admin.ModelAdmin):
    readonly_fields = ['room', 'user', 'user_pseudonym']
    list_display = ['__str__', 'room_id', 'user_id']


@admin.register(m.ExcalidrawFile)
class ExcalidrawFileAdmin(admin.ModelAdmin):
    readonly_fields = ['image']
    list_display = ['__str__', 'belongs_to_id', 'element_file_id']

    @admin.display(description=_("image"))
    def image(self, obj: m.ExcalidrawFile):
        return format_html(
            '<img src="{src}" title="{title}" style="max-width: 100%"/>',
            src=obj.content.url,
            title=_("image %s for room %s") % (obj.element_file_id, obj.belongs_to_id))

@admin.register(m.CourseToRoomMapper)
class CourseToRoomMapperAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'room_id', 'mode', 'lti_data_room']
