from pathlib import Path

import django
import pytest
import yaml
from aioworkers.core.config import Config
from aioworkers.core.context import Context
from django.core.management import call_command

from dvhb_hybrid import BASE_DIR

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
        'NAME': 'dvhb_hybrid',
    }
}


class Conf(Config):
    def load_yaml(self, s):
        self.update(yaml.load(s))


@pytest.fixture
def config():
    c = Conf()
    c.load_plugins(force=True)
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
def app(context):
    yield context.app


@pytest.fixture
def cli(app, test_client):
    # TODO Rename (cli is command line interface)
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
