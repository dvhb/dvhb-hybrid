import asyncio
import logging
from collections import ChainMap
from typing import Any, Optional, Tuple, Union, Mapping

import jinja2
from aioworkers.core.config import MergeDict
from aioworkers.core.context import Context
from aioworkers.utils import module_path
from aioworkers.worker.base import Worker

from .. import utils
from ..amodels import method_connect_once
from .template import EmailTemplate, load_all

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

    def set_config(self, config):
        super().set_config(config)

        mod = self.config.get('templates_from_module')
        if mod:
            path = module_path(mod, True)
            self.templates = load_all(self, path)
        else:
            self.templates = {}

        search_dirs = self.config.get('search_dirs')
        if search_dirs:
            loader = jinja2.FileSystemLoader(search_dirs)
        else:
            loader = None
        self._env = jinja2.Environment(loader=loader)

    async def init(self):
        await super().init()

        self.conf = self.config
        self.app = self.context.app
        self.app.mailer = self

        resource_name = 'monitor:mailer'
        status_url = self.config.get('status_url', '/monitor/mailer')
        if status_url:
            self.app.router.add_route(
                'GET', status_url,
                self.monitor,
                name=resource_name,
            )

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

    def _tempalte_names(
        self, template_name: str,
        lang_code: str,
        fallback_lang_code: str,
    ) -> Tuple[Union[str, Tuple[str, str]], ...]:
        return (
            (template_name, lang_code),
            (lang_code, template_name),
            (template_name, fallback_lang_code),
            (fallback_lang_code, template_name),
            template_name
        )

    async def get_dict_template(
        self, template_name: str, lang_code: str,
        fallback_lang_code: str ='en'
    ) -> Optional[EmailTemplate]:
        for i in self._tempalte_names(
            template_name,
            lang_code,
            fallback_lang_code,
        ):
            t = self.templates.get(i)
            if t:
                return t

    async def get_fs_template(
        self, template_name: str, lang_code: str,
        fallback_lang_code: str ='en'
    ) -> Optional[EmailTemplate]:
        names = []
        for n in self._tempalte_names(
            template_name + '.html',
            lang_code,
            fallback_lang_code,
        ):
            if isinstance(n, tuple):
                names.append('/'.join(n))
            else:
                names.append(n)
        try:
            t = self._env.select_template([self._env.select_template])
        except jinja2.TemplateNotFound:
            return None
        return EmailTemplate.create_from_jinja2(t)

    @method_connect_once
    async def get_db_template(
        self, template_name: str, lang_code: str,
        fallback_lang_code: str = 'en', connection: Any = None,
    ) -> Optional[EmailTemplate]:
        """
        Requests translation of the email template with name given to the language specified.
        If there is no translation to the requested language tries to find fallback one.

        On success returns translation in the form {'subject': TEMPLATE_SUBJECT, 'body': TEMPLATE_BODY}
        """

        # Try to find template with name given
        template = await self.app.models.email_template.get_by_name(template_name, connection=connection)
        if template is None:
            logger.info("No template name '%s' found in DB", template_name)
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
            return EmailTemplate(**translation.as_dict(self._env))
        else:
            logger.error(
                "No '%s' fallback translation for template name '%s' found in DB", fallback_lang_code, template_name)

    def get_context(self, *args, **kwargs) -> Mapping[str, Any]:
        url = self.context.config.http.get_url('url', '/', null=True)
        image_url = self.config.get_url('image_url', None, null=True)
        if image_url:
            image_url = url.join(image_url)
        else:
            image_url = url
        context = ChainMap(dict(image_url=str(image_url)))
        for m in args:
            if not m:
                continue
            elif not isinstance(m, Mapping):
                raise TypeError(
                    'context should be mapping, not {}'.format(type(context)))
            context = context.new_child(m)
        return context.new_child(kwargs)

    async def send(self, mail_to, subject=None, body=None, *, html=None,
                   context=None, connection=None, template=None, db_connection=None,
                   attachments=None, save=True, lang_code='en', fallback_lang_code='en'):
        if template:
            email_template = await self.get_db_template(
                template, lang_code, fallback_lang_code,
                connection=db_connection,
            )
            if not email_template:
                email_template = await self.get_fs_template(
                    template, lang_code, fallback_lang_code,
                )
            if not email_template:
                email_template = await self.get_dict_template(
                    template, lang_code, fallback_lang_code,
                )
            if not email_template:
                raise KeyError("No template named '{}'".format(template))
        else:
            email_template = EmailTemplate.create_from_str(
                subject=subject,
                body=body,
                html=html,
                env=self._env,
            )

        ctx = self.get_context(context)

        if not isinstance(mail_to, list):
            mail_to = mail_to.split(',')

        for recipient in mail_to:
            kwargs = dict(
                mail_to=[recipient],
                body=email_template.body.render(ctx, mail_to=recipient),
                subject=email_template.subject.render(ctx, mail_to=recipient),
                html=None,
                template=template,
                attachments=attachments,
            )
            if email_template.html:
                kwargs['html'] = email_template.html.render(ctx, mail_to=recipient)

            if save:
                message = await self.app.models.mail_message.create(
                    **kwargs, connection=db_connection)
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
