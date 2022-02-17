from django.contrib import admin

from . import models as m


@admin.register(m.ExcalidrawLogRecord)
class ExcalidrawLogRecordAdmin(admin.ModelAdmin):
    list_display = ["__str__", "room_name", "event_type"]
    fields = [
        "room_name",
        "event_type",
        "user_pseudonym",
        "content",
        ("_compressed", "compressed_size", "uncompressed_size", "compression_degree"),
        "created_at",
    ]
    readonly_fields = [
        "content", "_compressed", "compressed_size",
        "compression_degree", "uncompressed_size", "created_at"]


@admin.register(m.ExcalidrawRoom)
class ExcalidrawRoomAdmin(admin.ModelAdmin):
    readonly_fields = ['elements']
    # pass
