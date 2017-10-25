from django.conf.global_settings import LANGUAGES
from django.contrib.postgres.fields import JSONField, ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from dvhb_hybrid.models import UpdatedMixin


class Message(models.Model):
    mail_to = ArrayField(models.CharField(max_length=100))
    subject = models.TextField()
    body = models.TextField()
    template = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True)
    attachments = JSONField(default={}, blank=True, null=True)


class Template(UpdatedMixin, models.Model):
    name = models.CharField(_('name'), max_length=255, db_index=True)
    description = models.CharField(_('description'), max_length=1024, blank=True, null=True)

    class Meta:
        verbose_name = _('message template')
        verbose_name_plural = _('message templates')

    def __str__(self):
        return self.name


LANGUAGES_DICT = dict(LANGUAGES)


def validate_lang_code(value):
    if len(value) > 2:
        raise ValidationError(_("Please use ISO 639-1 two-letter language code"))
    if value not in LANGUAGES_DICT:
        raise ValidationError(_("Wrong language code specified"))


class TemplateTranslation(UpdatedMixin, models.Model):
    template = models.ForeignKey('mailer.Template')
    lang_code = models.CharField(_('language code'), max_length=2, validators=[validate_lang_code], db_index=True)
    message_subject = models.CharField(_('subject'), max_length=1024)
    message_body = models.CharField(_('body'), max_length=4096)

    class Meta:
        verbose_name = _('message template translation')
        verbose_name_plural = _('message template translations')
        unique_together = (('template', 'lang_code'),)

    @property
    def language(self):
        try:
            return LANGUAGES_DICT[self.lang_code]
        except KeyError:
            return _("Unknown")
