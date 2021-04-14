from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from ..utils import enum_to_choice
from .enums import UserActionLogEntryType, UserActionLogEntrySubType, UserActionLogStatus


class BaseUserActionLogEntry(models.Model):
    """
    Abstract action log entry django model class
    """

    created_at = models.DateTimeField(
        _('created at'),
        auto_now_add=True,
        editable=False
    )
    ip_address = models.CharField(_('user IP'), max_length=255, null=True)
    message = models.TextField(_('log message'))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.CASCADE,
        verbose_name=_('user'),
    )
    type = models.CharField(
        _('action type'),
        max_length=20,
        choices=enum_to_choice(UserActionLogEntryType)
    )
    subtype = models.CharField(
        _('action subtype'),
        max_length=20,
        choices=enum_to_choice(UserActionLogEntrySubType)
    )
    payload = models.JSONField(_('additional data'), null=True)
    status = models.CharField(
        _('action status'),
        max_length=20, null=True, blank=True,
        choices=enum_to_choice(UserActionLogStatus),
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, blank=True, null=True)
    object_id = models.TextField(_('object id'), blank=True, null=True)
    object_repr = models.CharField(_('object repr'), blank=True, null=True, max_length=200)

    def __str__(self):
        return str(self.created_at)

    class Meta:
        verbose_name = _('user action log record')
        ordering = ('-created_at',)
        abstract = True
