import json

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _


class CreatedMixin(models.Model):
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)

    class Meta:
        abstract = True


class UpdatedMixin(CreatedMixin):
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        abstract = True


class AuthorMixin(CreatedMixin):
    """
    Принадлежность к автору
    """
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                               verbose_name=_('Автор'))

    class Meta:
        abstract = True


class JSONFieldsMixin:

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        for f in self.jsonb_fields:
            v = getattr(self, f)
            if isinstance(v, str):
                try:
                    v = json.loads(v)
                except:
                    pass
                else:
                    setattr(self, f, v)
        super().save(force_insert, force_update, using, update_fields)
