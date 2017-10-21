from dvhb_hybrid.amodels import Model, method_connect_once

from .models import Template as DjangoTemplate
from .models import TemplateTranslation as DjangoTemplateTranslation


class EmailTemplate(Model):
    table = Model.get_table_from_django(DjangoTemplate)

    @classmethod
    @method_connect_once
    async def get_by_name(cls, name, connection=None):
        return await cls.get_one(cls.table.c.name == name, connection=connection, silent=True)

    @method_connect_once
    async def get_translation(self, lang_code='en', connection=None):
        return await EmailTemplateTranslation.get_template_translation(self.id, lang_code, connection=connection)


class EmailTemplateTranslation(Model):
    table = Model.get_table_from_django(DjangoTemplateTranslation)

    @classmethod
    @method_connect_once
    async def get_template_translation(cls, template_id, lang_code, connection=None):
        return await cls.get_one(
            (cls.table.c.template_id == template_id) & (cls.table.c.lang_code == lang_code),
            connection=connection,
            silent=True)

    def as_dict(self):
        return {
            'subject': self.message_subject,
            'body': self.message_body,
        }
