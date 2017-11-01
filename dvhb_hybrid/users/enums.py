import enum

from django.utils.translation import ugettext_lazy as _


class UserConfirmationRequestStatus(enum.Enum):
    created = 'created'
    sent = 'sent'
    confirmed = 'confirmed'
    cancelled = 'cancelled'

    @classmethod
    def translation(cls):
        return {
            cls.created: _('Created'),
            cls.sent: _('Sent'),
            cls.confirmed: _('Confirmed'),
            cls.cancelled: _('Cancelled'),
        }
