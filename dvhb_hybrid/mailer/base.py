import asyncio
import logging

from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context
from aioworkers.utils import module_path
from aioworkers.worker.base import Worker

from dvhb_hybrid.amodels import method_connect_once
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
        context = Context({}, loop=app.loop)
        context.app = app
        conf = MergeDict(conf)
        conf.name = 'mailer'
        m = cls(conf, context=context, loop=app.loop)

        async def start(app):
            await m.init()
            await m.start()

        app.on_startup.append(start)
        app.on_shutdown.append(lambda x: m.stop())

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
        mod = self.config.get('templates_from_module')
        if mod:
            path = module_path(mod, True)
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

    @method_connect_once
    async def get_template_translation(self, template_name, lang_code, fallback_lang_code='en', connection=None):
        """
        Requests translation of the email template with name given to the language specified.
        If there is no translation to the requested language tries to find fallback one.

        On success returns translation in the form {'subject': TEMPLATE_SUBJECT, 'body': TEMPLATE_BODY}
        """

        # Try to find template with name given
        template = await self.app.models.email_template.get_by_name(template_name, connection=connection)
        if template is None:
            logger.error("No template name '%s' found in DB", template_name)
            return
        # Try to find its translation to specifed language
        translation = await template.get_translation(lang_code, connection=connection)
        # Try to find fallback translation if necessary
        if translation is None:
            logger.warning(
                "No '%s' translation for template name '%s' found in DB, falling back to '%s'",
                lang_code, template_name, fallback_lang_code)
            translation = await template.get_translation(fallback_lang_code, connection=connection)
        if translation:
            return translation.as_dict()
        else:
            logger.error(
                "No '%s' fallback translation for template name '%s' found in DB", fallback_lang_code, template_name)

    async def send(self, mail_to, subject=None, body=None, *,
                   context=None, connection=None, template=None,
                   attachments=None, save=True, lang_code='en', fallback_lang_code='en'):
        if template:
            tr = await self.get_template_translation(template, lang_code, fallback_lang_code)
            if not tr:
                raise KeyError("No template named '{}' in DB".format(template))
            subject = tr['subject']
            body = tr['body']

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
