import uuid

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinLengthValidator
from django.db import models
from django.http import HttpRequest
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from pylti1p3.contrib.django.lti1p3_tool_config.models import LtiTool


class OneOffRegistrationLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consumer_name = models.CharField(
        _("consumer name"), max_length=64, blank=False, validators=[MinLengthValidator(5)],
        help_text=_("Name of the LTI consumer to register"))
    registered_consumer = models.OneToOneField(
        LtiTool, on_delete=models.CASCADE, null=True, blank=True,
        verbose_name=_("registered consumer"),
        help_text=_("only fills after registration completed"))
    consumer_registration_timestamp = models.DateTimeField(
        _("consumer registration timestamp"), null=True, blank=True)

    def get_uri(self, request: HttpRequest):
        return request.build_absolute_uri(reverse('lti:register-consumer', args=[self.pk]))

    def registration_complete(self, consumer: LtiTool):
        self.registered_consumer = consumer
        self.consumer_registration_timestamp = now()
        self.save()


class CustomUser(AbstractUser):
    """
    Custom User model.

    The model is needed to generate the user alias per room.
    This enables us to alias user for better privacy.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registered_via = models.ForeignKey(
        LtiTool, on_delete=models.CASCADE, null=True, verbose_name=_("registered via"))
