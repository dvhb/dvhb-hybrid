import pytest
from aiohttp.web import Application

import django
from django.conf import settings


def pytest_configure():
    settings.configure(
        INSTALLED_APPS=['dvhb_hybrid.mailer'],
    )
    django.setup()


@pytest.fixture
def app(loop):
    import dvhb_hybrid
    from dvhb_hybrid.amodels import AppModels
    AppModels.import_all_models_from_packages(dvhb_hybrid)
    application = Application(loop=loop)
    application.models = AppModels(application)
    return application
