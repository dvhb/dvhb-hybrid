from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import gettext_lazy as _

from dvhb_hybrid.utils import enum_to_choice
from .enums import UserActionLogEntryType, UserActionLogEntrySubType


class UserActionLogEntryManager(models.Manager):
    use_in_migrations = True


class UserActionLogEntry(models.Model):
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
    payload = JSONField(_('additional data'), null=True)

    objects = UserActionLogEntryManager()

    class Meta:
        verbose_name = _('user action log record')
        ordering = ('-created_at',)

    def __str__(self):
        return str(self.created_at)
