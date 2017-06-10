import asyncio
import logging

from aioworkers.core.context import Context
from aioworkers.utils import module_path
from aioworkers.worker.base import Worker

from .. import utils
from .template import load_all

logger = logging.getLogger('mailer')


class BaseConnection:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def send_message(self, message):
        raise NotImplementedError()

    async def open(self):
        raise NotImplementedError()

    async def close(self):
        raise NotImplementedError()

    async def __aenter__(self):
        return await self.open()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class BaseMailer(Worker):
    connection_class = BaseConnection

    @classmethod
    def setup(cls, app, conf):
        context = Context(loop=app.loop)
        context.app = app
        cls(conf, context=context, loop=app.loop)

    async def init(self):
        await super().init()

        self.conf = self.config
        self.app = self.context.app
        self.app.mailer = self
        self.app.router.add_route(
            'GET',
            self.config.get('status_url', '/monitor/mailer'),
            self.monitor,
            name='monitor:mailer',
        )
        path = module_path(self.config.templates_from_module, True)
        self.templates = load_all(self, path)

        self.mail_success = 0
        self.mail_failed = 0
        self.reconnect_counter = 0
        self.restart_counter = 0
        self.exception_counter = 0
        self.connect_counter = 0
        self.queue = asyncio.Queue(loop=self.loop)

    async def run(self, *args):
        while True:
            msg = await self.queue.get()
            async with self.get_connection() as conn:
                self.connect_counter += 1
                while True:
                    try:
                        await self.send_message(msg, conn)
                        self.mail_success += 1
                    except:
                        self.mail_failed += 1
                        await conn.close()
                        logger.exception('Mailer reconnect')
                        self.reconnect_counter += 1
                        await asyncio.sleep(2)
                        await conn.open()
                    try:
                        msg = self.queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break

    async def monitor(self, request):
        return dict(
            **await self.status(),
            mail_success=self.mail_success,
            mail_failed=self.mail_failed,
            reconnect_counter=self.reconnect_counter,
            connect_counter=self.connect_counter,
            restart_counter=self.restart_counter,
            exception_counter=self.exception_counter,
            queue=self.queue.qsize(),
            backend=self.config.cls,
        )

    def get_connection(self):
        connection = self.connection_class(
            loop=self.app.loop, conf=self.conf)
        return connection

    async def send(self, mail_to, subject=None, body=None, *,
                   context=None, connection=None, template=None,
                   attachments=None, save=True):
        if template:
            tmpl = self.templates[template]
            subject = tmpl['subject']
            body = tmpl['body']

        elif not subject or not body:
            raise ValueError()

        if not isinstance(context, dict):
            context = {}
        if isinstance(body, str):
            body = body.format(**context)
        else:
            body = body.render(**context)
        if isinstance(subject, str):
            subject = subject.format(**context)
        else:
            subject = subject.render(**context)

        if not isinstance(mail_to, list):
            mail_to = mail_to.split(',')

        kwargs = dict(
            body=body,
            subject=subject,
            template=template,
            attachments=attachments,
        )
        for recipient in mail_to:
            kwargs['mail_to'] = [recipient]
            if save:
                message = await self.app.models.mail_message.create(**kwargs)
            else:
                message = self.app.models.mail_message(**kwargs)

            if not connection:
                self.queue.put_nowait(message)
            else:
                await self.send_message(message, connection)
        return len(mail_to)

    async def send_message(self, message, connection):
        await connection.send_message(message)
        message.sent_at = utils.now()
        if message.pk:
            await message.save(fields=['sent_at'])
