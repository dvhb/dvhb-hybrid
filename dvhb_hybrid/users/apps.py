from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = 'dvhb_hybrid.users'
    label = 'dvhb_hybrid_users'
    verbose_name = _('users')
