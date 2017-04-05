from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models


class Message(models.Model):
    mail_to = ArrayField(models.CharField(max_length=100))
    subject = models.TextField()
    body = models.TextField()
    template = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True)
    attachments = JSONField(default={}, blank=True, null=True)
