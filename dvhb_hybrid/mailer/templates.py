from dvhb_hybrid.amodels import method_connect_once
from .amodels import EmailTemplate


@method_connect_once
async def get_template_translation(template_name, lang_code, fallback_lang_code='en', connection=None):
    """
    Requests translation of the email template with name given to the language specified.
    If there is no translation to the requested language tries to find fallback one.

    On success returns translation in the form {'subject': TEMPLATE_SUBJECT, 'body': TEMPLATE_BODY}
    """

    # Try to find template with name given
    template = await EmailTemplate.get_by_name(template_name, connection=connection)
    if template is None:
        return
    # Try to find its translation to specifed language
    translation = await template.get_translation(lang_code, connection=connection)
    # Try to find fallback translation if necessary
    if translation is None:
        translation = await template.get_translation(fallback_lang_code, connection=connection)
    if translation:
        return translation.as_dict()
