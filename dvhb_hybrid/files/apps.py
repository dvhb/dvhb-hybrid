from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class FilesConfig(AppConfig):
    name = 'dvhb_hybrid.files'
    verbose_name = _('Файлы')
