import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils.translation import ugettext_lazy as _

from ..models import UpdatedMixin, SVGAndImageField
from .storages import image_storage


class Image(UpdatedMixin, models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='images',
        verbose_name=_('Author'), on_delete=models.PROTECT)
    uuid = models.UUIDField(_('UUID'), primary_key=True)
    image = SVGAndImageField(storage=image_storage)
    mime_type = models.CharField(_('content type'), max_length=99, blank=True)
    meta = models.JSONField(_('meta-information'), default=dict, blank=True)

    class Meta:
        verbose_name = _('image')
        verbose_name_plural = _('images')
        ordering = ('-created_at',)
        indexes = [GinIndex(fields=['meta'])]

    def __str__(self):
        return self.image.name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.uuid:
            uid = uuid.uuid4()
            self.uuid = uid
            self.image.name = image_storage.get_available_name(
                self.image.name, uuid=uid)

        super(Image, self).save(force_insert=force_insert,
                                force_update=force_update,
                                using=using,
                                update_fields=update_fields)
