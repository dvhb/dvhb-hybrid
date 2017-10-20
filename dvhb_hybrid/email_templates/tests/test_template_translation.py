import pytest


@pytest.mark.django_db
async def test_get_template_by_name(app, test_client):
    await test_client(app)  # to initialize DB
    template_name = 'AccountActivation'
    template = await app.m.email_template.get_by_name(template_name)
    assert template is not None


@pytest.mark.django_db
async def test_get_tranlations(app, test_client):
    await test_client(app)  # to initialize DB
    template_name = 'AccountActivation'
    template = await app.m.email_template.get_by_name(template_name)
    translation = await template.get_translation('en')
    assert translation is not None
    translation = await template.get_translation('ru')
    assert translation is not None
