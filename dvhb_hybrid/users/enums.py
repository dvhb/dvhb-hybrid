import enum

from django.utils.translation import ugettext_lazy as _


class UserActivationRequestStatus(enum.Enum):
    sent = 'sent'
    activated = 'activated'

    @classmethod
    def translation(cls):
        return {
            cls.sent: _('Sent'),
            cls.activated: _('Activated'),
        }
