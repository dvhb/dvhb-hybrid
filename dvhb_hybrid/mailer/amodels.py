from dvhb_hybrid.amodels import Model
from dvhb_hybrid import utils

from .models import Message


class MailMessage(Model):
    table = Model.get_table_from_django(Message, 'attachments')

    @classmethod
    def set_defaults(cls, data: dict):
        data.setdefault('created_at', utils.now())
