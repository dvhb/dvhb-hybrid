import logging
import pytest
from aioworkers.core.context import Context, GroupResolver

import django
from django.core.management import call_command

from dvhb_hybrid import BASE_DIR
from dvhb_hybrid.tests import AuthClient
from dvhb_hybrid.utils import import_class

from .settings import config

logger = logging.getLogger(__name__)
pytest_plugins = ['dvhb_hybrid.tests']


def pytest_configure():
    django.setup()


class TestClient(AuthClient):
    base_path = '/api/1'

    async def ensure_user(self, new_user=False, **kwargs):
        pass


@pytest.fixture
def client_class():
    return TestClient


@pytest.fixture
def groups():
    return dict(
        include={'web'},
    )


@pytest.fixture
def context(loop, groups):
    gr = GroupResolver(**groups)
    with Context(config=config, loop=loop, group_resolver=gr) as ctx:
        yield ctx


@pytest.fixture
def app(context):
    return context.app


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
        names.append(i.with_suffix('').name)
    if names:
        with django_db_blocker.unblock():
            call_command('loaddata', *names)


@pytest.fixture
def make_request(app, test_client):
    async def wrapper(
            url, url_params={}, url_query={}, method='post', client=None, json=None, data=None, expected_status=None,
            decode_json=True, cookies={}):
        client = client or await test_client(app)
        if cookies:
            client.session.cookie_jar.update_cookies(cookies)
        method_fn = getattr(client, method)
        if url_params or url_query:
            url = app.router[url].url_for(**url_params)
            if url_query:
                url = url.with_query(**url_query)
        response = await method_fn(url, json=json, data=data)
        if expected_status:
            assert response.status == expected_status, await response.text()
        if decode_json:
            try:
                return await response.json()
            except Exception as e:
                logger.error("Failed to decode JSON from response text '%s' (%s)", await response.text(), e)
                raise
        else:
            return await response.read()
    return wrapper
