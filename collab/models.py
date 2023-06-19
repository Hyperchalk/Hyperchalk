import mimetypes
from functools import cached_property
from hashlib import sha256
from sqlite3 import IntegrityError
from typing import Optional, TypeVar
from urllib.request import urlopen

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool

from draw.utils import (JSONType, bytes_to_data_uri, compression_ratio, dump_content, load_content, make_room_name,
                        pick, uncompressed_json_size, user_id_for_room, validate_room_name)
from ltiapi.models import CustomUser
from ltiapi.utils import get_legacy_user_room_name

from .types import ALLOWED_IMAGE_MIME_TYPES, ExcalidrawBinaryFile

TPseudonym = TypeVar('TPseudonym', bound='Pseudonym')
TRoom = TypeVar('TRoom', bound='ExcalidrawRoom')


class ExcalidrawLogRecordManager(models.Manager):
    def records_for_pseudonym(self, pseudonym: TPseudonym):
        return self.get_queryset().filter(user_pseudonym=pseudonym.user_pseudonym)

    def records_for_user_in_room(self, user: CustomUser, room: TRoom):
        return self.get_queryset().filter(user_pseudonym=models.Subquery(
            Pseudonym.objects.filter(user=user, room=room).values('user_pseudonym')[:1]
        ))


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
    room_name = models.CharField(max_length=24, validators=[validate_room_name])
    event_type = models.CharField(max_length=50)
    # if a user is deleted, keep the foreign key to be able to keep the action log
    user_pseudonym = models.CharField(
        max_length=64, validators=[MinLengthValidator(64)], null=True,
        help_text=_("this is generated from draw.utils.user_id_for_room"))
    _content = models.BinaryField(blank=True)

    objects = ExcalidrawLogRecordManager()

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
        return uncompressed_json_size(self.content)

    @property
    def compression_degree(self):
        return compression_ratio(self)

    @property
    def user(self) -> Optional[CustomUser]:
        """
        :returns: user if there is one in the pseudonym table
        """
        try:
            return Pseudonym.objects.get(user_pseudonym=self.user_pseudonym).user
        except Pseudonym.DoesNotExist:
            return None

    @user.setter
    def user(self, user: CustomUser):
        self.user_pseudonym = user_id_for_room(user.pk, self.room_name) if user else None

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
        validators=[validate_room_name])
    room_created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    room_consumer = models.ForeignKey(LtiTool, on_delete=models.SET_NULL, null=True, blank=True)
    room_course_id = models.CharField(max_length=255, null=True, blank=True)
    tracking_enabled = models.BooleanField(_("track users' actions"), default=settings.ENABLE_TRACKING_BY_DEFAULT)
    _elements = models.BinaryField(blank=True, default=EMPTY_JSON_LIST_ZLIB_COMPRESSED)

    @property
    def elements(self):
        return load_content(self._elements, compressed=True)

    @elements.setter
    def elements(self, val: JSONType = None):
        self._elements = dump_content(val, force_compression=True)

    @cached_property
    def compressed_size(self):
        return len(self._elements)

    @cached_property
    def uncompressed_size(self):
        return uncompressed_json_size(self.elements)

    @property
    def compression_degree(self):
        return compression_ratio(self)

    def clone(self, *, room_course_id: str, room_created_by: CustomUser, room_consumer: LtiTool):
        """
        Clone a room and its associated files.

        This will insert the room as a new log record. So the replay of the
        cloned room will begin from the moment where the clone was created.
        """
        # get the files from the original room
        files = list(self.files.all())

        # clone the board
        old_name = self.room_name
        self.pk = None
        self.room_name = make_room_name(24)
        self.room_course_id = room_course_id
        self.room_consumer = room_consumer
        self.save()

        # clone the files
        for f in files:
            f.pk = None
            f.belongs_to = self
        ExcalidrawFile.objects.bulk_create(files)

        # make visible that this room was cloned
        record = ExcalidrawLogRecord(room_name=self.room_name, event_type="cloned")
        record.user = room_created_by
        record.content = {'clonedFrom': old_name}
        record.save()

        # insert the room as a new log record. the replay
        # will begin from the moment the room is cloned.
        record = ExcalidrawLogRecord(room_name=self.room_name, event_type="full_sync")
        record.user = room_created_by
        record.content = self.elements
        record.save()

        return self


class Pseudonym(models.Model):
    """
    Table that stores which user belongs to which pseudonym.

    Delete all records in this table to restore anonymity. No
    record will be available for users who joined anonymously.
    """
    room = models.ForeignKey(ExcalidrawRoom, on_delete=models.CASCADE, verbose_name=_("room name"))
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name=_("user"))
    user_pseudonym = models.CharField(
        primary_key=True, max_length=64, validators=[MinLengthValidator(64)],
        help_text=_("this is generated from draw.utils.user_id_for_room"))

    class Meta:
        unique_together = [('room', 'user')]

    @classmethod
    def create_for_user_in_room(cls, user: CustomUser, room: ExcalidrawRoom):
        return cls(room=room, user=user, user_pseudonym=user_id_for_room(user.pk, room.room_name))

    @classmethod
    def stored_pseudonym_for_user_in_room(cls, user: CustomUser, room: ExcalidrawRoom) -> str:
        self = cls.create_for_user_in_room(user, room)
        try:
            self.save()
        except IntegrityError:
            # if the pseudonym is already stored, this error
            # can be ignored because the data will never change.
            pass
        return self.user_pseudonym


class ExcalidrawFile(models.Model):
    """
    File store

    WARNING: don't delete the content file until there is no room which uses it anymore.

    Orphaned files can be deleted from the admin view.
    """
    belongs_to = models.ForeignKey(
        ExcalidrawRoom, on_delete=models.SET_NULL, null=True,
        related_name="files", verbose_name=_("belongs to room"))
    # we don't use the hash that's submitted by excalidraw as the pk
    # because it is a sha1 hash and sha1 is broken. for filtering, this
    # should therefore only be used on the relation manager of belongs_to.
    element_file_id = models.CharField(max_length=40)
    # file content will be stored as file, not to db
    content = models.FileField(upload_to='excalidraw-uploads')
    # this will not be compressed, as the file meta data is always relatively small in size.
    meta = models.JSONField(verbose_name=_("excalidraw meta data"))

    ALLOWED_META_KEYS = {'created', 'mimeType'}

    class Meta:
        unique_together = [('belongs_to', 'element_file_id')]

    @classmethod
    def from_excalidraw_file_schema(cls, room_name: str, file_data: ExcalidrawBinaryFile):
        mime_from_data_uri, _ = mimetypes.guess_type(file_data.dataURL)
        if mime_from_data_uri not in ALLOWED_IMAGE_MIME_TYPES:
            raise ValidationError({
                "content": _("The content MIME type of %s is not allowed") % (mime_from_data_uri,)
            })
        file_data.mimeType = mime_from_data_uri # consider data from the client as being unsafe
        with urlopen(file_data.dataURL) as response:
            content_bytes = response.read()
        file_hash = sha256(content_bytes)
        file_name = file_hash.hexdigest() + (mimetypes.guess_extension(mime_from_data_uri) or "")

        self = cls(
            belongs_to_id=room_name,
            content=ContentFile(content_bytes, name=file_name),
            element_file_id=file_data.id,
            meta=pick(file_data.dict(), cls.ALLOWED_META_KEYS))
        return self

    def to_excalidraw_file_schema(self) -> ExcalidrawBinaryFile:
        return ExcalidrawBinaryFile(
            **self.meta,
            id=self.element_file_id,
            dataURL=bytes_to_data_uri(self.content.read(), self.meta['mimeType']),
            filePath=self.content.url)

    def __repr__(self) -> str:
        return f"<ExcalidrawFile {self.element_file_id} for room {self.belongs_to_id}>"


class CourseToRoomMapperManager(models.Manager):
    def create_from_room_name(
        self, *, lti_data_room: str, course_id: str,
        mode: str, user: CustomUser,  lti_tool: LtiTool
    ) -> models.Model:
        """
        Create or clone a room if necessary, returning a mapper to it.
        """
        Modes = self.model.BoardMode

        room = ExcalidrawRoom.objects\
            .filter(room_name=lti_data_room)\
            .first()

        if room and room.room_course_id == course_id:
            # the room is opened from the course it was created in
            new_room = room
        elif room:
            # the room exists but is openend from a cloned course
            new_room = room.clone(
                room_course_id=course_id,
                room_created_by=user,
                room_consumer=lti_tool)
        else:
            # the room was not created yet. the course might
            # have been cloned but it does not matter here.
            new_room_name = make_room_name(24) if mode == Modes.STUDENT else lti_data_room
            new_room = ExcalidrawRoom(
                room_name=new_room_name,
                room_created_by=user,
                room_consumer=lti_tool,
                room_course_id=course_id,
                tracking_enabled=settings.ENABLE_TRACKING_BY_DEFAULT_FOR_LTI)
            new_room.save()

        redirect = self.model(
            room=new_room, lti_data_room=lti_data_room, course_id=course_id, mode=mode,
            user=user if mode in [Modes.STUDENT, Modes.STUDENT_LEGACY] else None)
        redirect.clean()
        redirect.save()

        return redirect

    def get_or_create_for_course(
        self, *, lti_data_room: str, course_id: str,
        mode: str, user: CustomUser, lti_tool: LtiTool
    ) -> tuple[models.Model, bool]:
        """ Creates a redirect and clones a corresponding room if neccessary. """
        Modes = self.model.BoardMode

        try:
            # happy path: the room has already been requested from a course
            if mode == Modes.STUDENT:
                redirect = self.get(lti_data_room=lti_data_room, course_id=course_id, user=user.id)
            elif mode == Modes.STUDENT_LEGACY:
                lti_data_room = get_legacy_user_room_name(lti_data_room, user)
                redirect = self.get(lti_data_room=lti_data_room, course_id=course_id, user=user.id)
            else:
                redirect = self.get(lti_data_room=lti_data_room, course_id=course_id)
            return redirect, False

        except self.model.DoesNotExist:
            pass

        # the room may have existed before and was opened from the course it was created on.
        # legacy single does not have to be implemented here as it would have been created above
        # for Modes.STUDENT_LEGACY, lti_data_room is still the full legacy room name
        redirect = self.create_from_room_name(
            lti_data_room=lti_data_room, course_id=course_id,
            mode=mode, user=user, lti_tool=lti_tool)

        return redirect, True


class CourseToRoomMapper(models.Model):
    """
    Redirect to a board based on (lti data, course id, user name)

    Since courses containing a board can be cloned, we want to clone the boards, too. The problem
    with this is that the LTI custom data can't be changed without calling the configuration again.
    To deal with this, this class provides a course cloning detection mechanism, redicreting users
    to the appropriate boards. The ids translate as follows::

        mode classroom:
            (lti data, course id) -> room name

        mode group:
            (lti data, course id) -> room name

        mode single:
            (lti prefix, course id, user) -> room name
    """
    class BoardMode(models.TextChoices):
        CLASSROOM      = "classroom", _("Classroom Assignment")
        GROUPWORK      = "group",     _("Group Assignment")
        STUDENT        = "single_v2", _("Single Student")
        STUDENT_LEGACY = "single",    _("Single Student Assignment (legacy)")

    room = models.OneToOneField(
        ExcalidrawRoom, primary_key=True, related_name="course",
        on_delete=models.CASCADE, verbose_name=_("room name"))
    lti_data_room = models.CharField(max_length=24, validators=[validate_room_name])
    mode = models.CharField(
        max_length=12, verbose_name=_("board mode"),
        choices=BoardMode.choices, default=BoardMode.CLASSROOM)
    course_id = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, blank=True, null=True, verbose_name=_("user"))

    objects = CourseToRoomMapperManager()

    class Meta:
        unique_together = [("lti_data_room", "course_id", "user")]

    def clean(self):
        if self.user and self.mode not in [self.BoardMode.STUDENT, self.BoardMode.STUDENT_LEGACY]:
            raise ValidationError({
                "user": _("The user can only be set if the mode is set to “single student”"),
            })
