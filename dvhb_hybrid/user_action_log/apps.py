from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UserActionLogConfig(AppConfig):
    name = 'dvhb_hybrid.user_action_log'
    verbose_name = _('UserActionLog')
