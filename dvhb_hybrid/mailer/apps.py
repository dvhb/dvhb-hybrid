from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class MailerConfig(AppConfig):
    name = 'dvhb_hybrid.mailer'
    verbose_name = _('Mailer')
