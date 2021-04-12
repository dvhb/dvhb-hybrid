from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class UsersConfig(AppConfig):
    name = 'dvhb_hybrid.users'
    label = 'dvhb_hybrid_users'
    verbose_name = _('users')
