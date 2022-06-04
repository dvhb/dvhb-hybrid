import smtplib
from concurrent.futures import ThreadPoolExecutor
from email.mime.text import MIMEText
from functools import partial

from . import base


class SMTPConnection(base.BaseConnection):
    def __init__(self, loop, conf, **kwargs):
        super().__init__(**kwargs)
        self._conn = None
        self.loop = loop
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.conf = conf

    async def send_message(self, message):
        if not self._conn:
            raise ConnectionError()
        msg = MIMEText(message.body)
        msg['To'] = ', '.join(message.mail_to)
        msg['Subject'] = message.subject
        msg['From'] = self.conf.from_email
        return await self.loop.run_in_executor(
            self.executor, self._conn.send_message, msg)

    async def open(self):
        await self.close()
        if not self._conn:
            self._conn = smtplib.SMTP()
        connect = partial(self._conn.connect, **self.conf.mta)
        await self.loop.run_in_executor(self.executor, connect)
        return self

    async def close(self):
        if self._conn:
            await self.loop.run_in_executor(
                self.executor, self._conn.close)


class Mailer(base.BaseMailer):
    connection_class = SMTPConnection
