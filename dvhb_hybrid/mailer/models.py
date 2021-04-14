import os

from django.conf.global_settings import LANGUAGES
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _

from ..models import UpdatedMixin


class Message(models.Model):
    mail_to = ArrayField(models.CharField(max_length=100))
    subject = models.TextField()
    body = models.TextField()
    html = models.TextField(null=True)
    template = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True)
    attachments = models.JSONField(default=dict, blank=True, null=True)


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


def template_target(instance, filename):
    ext = os.path.splitext(filename)[-1].lower()
    return 'mails/{0.template.name}/{0.lang_code}/mail{1}'.format(instance, ext)


def validate_file_extension(value):
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.html', '.htm', '.jade']
    if ext not in valid_extensions:
        raise ValidationError(_('Unsupported file extension'))


class TemplateTranslation(UpdatedMixin, models.Model):
    template = models.ForeignKey('mailer.Template', on_delete=models.PROTECT)
    lang_code = models.CharField(_('language code'), max_length=2, validators=[validate_lang_code], db_index=True)
    message_subject = models.CharField(_('subject'), max_length=1024)
    message_body = models.CharField(_('body'), max_length=4096)
    file_html = models.FileField(
        _('html'), null=True, blank=True,
        upload_to=template_target,
        validators=[validate_file_extension])

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

    def __str__(self):
        return self.language
