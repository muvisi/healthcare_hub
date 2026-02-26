# trigger/models.py
from django.db import models
import uuid

class TriggerLog(models.Model):
    """
    Central log for all triggers/actions across all sections.
    """
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    section = models.CharField(max_length=100)  # e.g., "Members", "Benefits"
    action = models.CharField(max_length=100, default="push")  # optional: type of action
    member_no = models.CharField(max_length=50, null=True, blank=True)  # optional, for Members
    extra_info = models.JSONField(null=True, blank=True)  # optional: store any extra data
    triggered_by = models.CharField(max_length=150, null=True, blank=True)  # username
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.section} - {self.action} by {self.triggered_by}"