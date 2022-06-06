from .. import utils
from ..amodels import Model, method_connect_once
from .models import Message
from .models import Template as DjangoTemplate
from .models import TemplateTranslation as DjangoTemplateTranslation
from .template import FormatRender, Jinja2Render


class MailMessage(Model):
    table = Model.get_table_from_django(Message, 'attachments')

    @classmethod
    def set_defaults(cls, data: dict):
        data.setdefault('created_at', utils.now())


class EmailTemplate(Model):
    table = Model.get_table_from_django(DjangoTemplate)

    @classmethod
    @method_connect_once
    async def get_by_name(cls, name, connection=None):
        return await cls.get_one(cls.table.c.name == name, connection=connection, silent=True)

    @method_connect_once
    async def get_translation(self, lang_code='en', connection=None):
        trans = self.models['email_template_translation']
        if trans.app is None:  # warm up
            trans = trans.factory(self.app)
        return await trans.get_template_translation(
            self.id, lang_code, connection=connection)


class EmailTemplateTranslation(Model):
    table = Model.get_table_from_django(DjangoTemplateTranslation)

    @classmethod
    @method_connect_once
    async def get_template_translation(cls, template_id, lang_code, connection=None):
        return await cls.get_one(
            (cls.table.c.template_id == template_id) & (cls.table.c.lang_code == lang_code),
            connection=connection,
            silent=True)

    def as_dict(self, env=None):
        data = {
            'subject': FormatRender(self.message_subject),
            'body': FormatRender(self.message_body),
        }
        html = self.file_html
        if html:
            data['html'] = Jinja2Render(env=env, template_name=html)
        else:
            data['html'] = None
        return data
