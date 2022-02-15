from email.policy import default
from django.db import models

class ExcalidrawLogRecord(models.Model):
    """
    Contains events from the Websocket Collab endpoint.
    """
    content = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    log_type = models.CharField(max_length=50)
    user = models.CharField(max_length=50)
