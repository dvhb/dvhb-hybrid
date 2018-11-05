from pathlib import Path

import aiopg.sa
import pytest
from aiohttp.web import Application

import django
from django.core.management import call_command
from aioworkers.core.config import Config
from aioworkers.core.context import Context

from dvhb_hybrid import BASE_DIR
from dvhb_hybrid.utils import import_class


TESTS_DIR = Path(__file__).parent

# Django settings
SECRET_KEY = '123'
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'dvhb_hybrid.users',
    'dvhb_hybrid.mailer',
    'dvhb_hybrid.user_action_log',
    'tests',
]
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'dvhb_hybrid_app',
    }
}


@pytest.fixture
def config():
    c = Config()
    c.load(
        TESTS_DIR / 'config.yaml',
    )
    return c


@pytest.fixture
def context(config, loop):
    with Context(config, loop=loop) as ctx:
        yield ctx


def pytest_configure():
    django.setup()


@pytest.fixture
def app(context, loop):
    import dvhb_hybrid
    from dvhb_hybrid.amodels import AppModels

    db = aiopg.sa.create_engine(database='test_dvhb_hybrid_app', loop=loop)
    context.db = db

    app = Application(loop=loop)
    context.app = app
    app['db'] = loop.run_until_complete(db.__aenter__())

    AppModels.import_all_models_from_packages(dvhb_hybrid)
    app.models = app.m = AppModels(app)

    Mailer = import_class('dvhb_hybrid.mailer.django.Mailer')
    Mailer.setup(app, {'from_email': 'no-replay@dvhb.ru'})

    yield app

    loop.run_until_complete(db.__aexit__(None, None, None))


@pytest.fixture
def cli(app, test_client):
    async def create_client():
        client = await test_client(app)
        return client
    return create_client


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Creates and initializes test DB
    """
    names = []
    for i in BASE_DIR.glob('*/fixtures/*yaml'):
        # TODO: Split test fixtures
        # Do not import fixtures from users app
        if i.parent.parent.name == 'users':
            continue
        names.append(i.with_suffix('').name)
    with django_db_blocker.unblock():
        call_command('loaddata', *names)
