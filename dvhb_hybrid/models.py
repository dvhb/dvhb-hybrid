import json

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import get_available_image_extensions, FileExtensionValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .utils import validate_svg_file


class CreatedMixin(models.Model):
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        abstract = True


class UpdatedMixin(CreatedMixin):
    updated_at = models.DateTimeField(_('update at'), auto_now=True)

    class Meta:
        abstract = True


class AuthorMixin(CreatedMixin):
    author = models.ForeignKey(settings.AUTH_USER_MODEL,
                               verbose_name=_('author'),
                               on_delete=models.PROTECT)

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


def validate_image_and_svg_file_extension(value):
    allowed_extensions = get_available_image_extensions() + ["svg"]
    return FileExtensionValidator(allowed_extensions=allowed_extensions)(value)


class SVGAndImageFieldForm(forms.ImageField):
    default_validators = [validate_image_and_svg_file_extension]

    def to_python(self, data):
        try:
            f = super().to_python(data)
        except ValidationError:
            return validate_svg_file(data)
        return f


class SVGAndImageField(models.ImageField):
    def formfield(self, **kwargs):
        defaults = {'form_class': SVGAndImageFieldForm}
        defaults.update(kwargs)
        return super().formfield(**defaults)
