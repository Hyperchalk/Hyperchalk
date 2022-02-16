from functools import cached_property
import json

from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator
from django.db import models

from .utils import JSONType, dump_content, load_content


class ExcalidrawLogRecord(models.Model):
    """
    Contains events from the Websocket Collab endpoint.

    The content field may be compressed via zlib. The ``_compressed`` field holds the information
    if the content has been compressed. The decompression does not have to take place manually. Use
    the properties of this model therefore.
    """
    # dates are sorted after field size. this reduces table size in postgres.
    _compressed = models.BooleanField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    room_name = models.CharField(max_length=24, validators=[MinLengthValidator(24)])
    event_type = models.CharField(max_length=50)
    # if a user is deleted, keep the foreign key to be able to keep the action log
    user = models.ForeignKey(get_user_model(), on_delete=models.DO_NOTHING, null=True)
    _content = models.BinaryField(blank=True)

    @property
    def content(self):
        return load_content(self._content, self._compressed)

    @content.setter
    def content(self, val: JSONType = None):
        self._content, self._compressed = dump_content(val)

    @cached_property
    def compressed_size(self):
        return len(self._content)

    @cached_property
    def uncompressed_size(self):
        return len(json.dumps(self.content, ensure_ascii=False).encode('utf-8'))

    @property
    def compression_degree(self):
        comp = 100 - self.compressed_size / self.uncompressed_size * 100
        return f"{comp:.2f} %"


class ExcalidrawRoom(models.Model):
    """
    Contains the latest ``ExcalidrawElement`` s of a room.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)
    room_name = models.CharField(
        primary_key=True, max_length=24,
        validators=[MinLengthValidator(24)])
    _elements = models.BinaryField(blank=True)

    @property
    def elements(self):
        return load_content(self._elements, compressed=True)

    @elements.setter
    def elements(self, val: JSONType = None):
        self._elements = dump_content(val, force_compression=True)
