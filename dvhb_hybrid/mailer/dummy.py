from email.mime.text import MIMEText
from typing import List

from . import base


class Connection(base.BaseConnection):
    messages: List[MIMEText] = []

    def __init__(self, conf, **kwargs):
        super().__init__(**kwargs)
        self.conf = conf

    async def send_message(self, message):
        msg = MIMEText(message.body)
        msg['To'] = ', '.join(message.mail_to)
        msg['Subject'] = message.subject
        msg['From'] = self.conf.from_email
        self.messages.append(msg)

    async def open(self):
        return self

    async def close(self):
        pass


class Mailer(base.BaseMailer):
    connection_class = Connection

    def clean(self):
        self.connection_class.messages = []

    @property
    def messages(self):
        return self.connection_class.messages
