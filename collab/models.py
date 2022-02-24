import json
from functools import cached_property

from django.core.validators import MinLengthValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from draw.utils import JSONType, dump_content, load_content
from ltiapi.models import CustomUser


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
    user_pseudonym = models.CharField(
        max_length=40, validators=[MinLengthValidator(40)], null=True,
        help_text=_("this is geenrated from ltiapi.models.CustomUser.id_for_room"))
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

    @property
    def user(self):
        return None

    @user.setter
    def user(self, user: CustomUser):
        self.user_pseudonym = user.id_for_room(self.room_name)

# trust me
EMPTY_JSON_LIST_ZLIB_COMPRESSED = b'x\x9c\x8b\x8e\x05\x00\x01\x15\x00\xb9'

class ExcalidrawRoom(models.Model):
    """
    Contains the latest ``ExcalidrawElement`` s of a room.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)
    room_name = models.CharField(
        primary_key=True, max_length=24,
        validators=[MinLengthValidator(24)])
    # TODO: log channel name if a user is logged in in multiple tabs / windows
    # via_channel = models.CharField()
    _elements = models.BinaryField(blank=True, default=EMPTY_JSON_LIST_ZLIB_COMPRESSED)

    @property
    def elements(self):
        return load_content(self._elements, compressed=True)

    @elements.setter
    def elements(self, val: JSONType = None):
        self._elements = dump_content(val, force_compression=True)
