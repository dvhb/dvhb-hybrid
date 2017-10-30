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


class UserProfileDeleteRequestStatus(enum.Enum):
    created = 'created'
    sent = 'sent'
    confirmed = 'confirmed'

    @classmethod
    def translation(cls):
        return {
            cls.created: _('Created'),
            cls.sent: _('Sent'),
            cls.confirmed: _('Confirmed'),
        }
