import base64
from concurrent.futures import ThreadPoolExecutor

from django.core import mail

from . import base


class DjangoConnection(base.BaseConnection):
    def __init__(self, loop, conf, **kwargs):
        super().__init__(**kwargs)
        self.loop = loop
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._conn = None
        self.conf = conf

    async def send_message(self, message):
        if not self._conn:
            raise ConnectionError()
        msg = mail.EmailMessage(
            subject=message.subject,
            body=message.body,
            from_email=self.conf['from_email'],
            to=message.mail_to,
            connection=self._conn,
        )

        def attach_files(message, attachments):
            if attachments:
                for attachment in attachments:
                    path = attachment.get('path')
                    filename = attachment.get('filename')
                    mimetype = attachment.get('mimetype')
                    if path:
                        message.attach_file(path, mimetype=mimetype)
                    elif filename:
                        content = attachment.get('content')
                        if content:
                            message.attach(filename,
                                           base64.decodebytes(
                                               content.encode()),
                                           mimetype)
        await self.loop.run_in_executor(self.executor, attach_files,
                                        msg, message.attachments)
        return await self.loop.run_in_executor(self.executor, msg.send)

    async def close(self):
        if self._conn:
            await self.loop.run_in_executor(
                self.executor, self._conn.close)

    async def open(self):
        await self.close()
        if not self._conn:
            params = {
                'backend': self.conf.get('django_email_backend'),
                **self.conf.get('django_email_backend_params', {}),
            }
            self._conn = mail.get_connection(**params)
        await self.loop.run_in_executor(self.executor, self._conn.open)
        return self


class Mailer(base.BaseMailer):
    connection_class = DjangoConnection
