import aiopg.sa
import pytest
from aiohttp.web import Application

import django
from django.conf import settings

from dvhb_hybrid.utils import import_class


def pytest_configure():
    settings.configure(
        INSTALLED_APPS=['dvhb_hybrid.mailer'],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': 'dvhb_hybrid_app',
            }
        },
    )
    django.setup()


@pytest.fixture
def app(loop):
    import dvhb_hybrid
    from dvhb_hybrid.amodels import AppModels

    async def startup_database(app):
        app['db'] = await aiopg.sa.create_engine(database='test_dvhb_hybrid_app', loop=loop)

    async def cleanup_database(app):
        async with app['db']:
            pass

    application = Application(loop=loop)
    application.on_startup.append(startup_database)
    application.on_cleanup.append(cleanup_database)

    AppModels.import_all_models_from_packages(dvhb_hybrid)
    application.models = AppModels(application)

    Mailer = import_class('dvhb_hybrid.mailer.django.Mailer')
    Mailer.setup(application, {'from_email': 'no-replay@dvhb.ru'})

    return application


@pytest.fixture
def cli(app, test_client):
    async def create_client():
        client = await test_client(app)
        return client
    return create_client
