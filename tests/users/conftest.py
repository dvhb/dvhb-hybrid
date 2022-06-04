import logging
from types import MappingProxyType
from uuid import uuid4

import pytest
from django.contrib.auth.hashers import make_password


logger = logging.getLogger(__name__)


@pytest.fixture
def make_request(app, test_client):
    async def wrapper(
        url, method='post',
        url_params=MappingProxyType({}),
        url_query='',
        client=None,
        cookies=MappingProxyType({}),
        json=None, data=None, decode_json=True,
        allow_redirects=True, expected_status=None,
    ):
        client = client or await test_client(app)
        if cookies:
            client.session.cookie_jar.update_cookies(cookies)
        if isinstance(url, str) and not url.startswith('/'):
            url = app.router[url].url_for(**url_params)
        if url_query:
            url = url.with_query(url_query)
        response = await client.request(
            method, url, json=json, data=data,
            allow_redirects=allow_redirects)
        if expected_status:
            assert response.status == expected_status, await response.text()
        if decode_json:
            try:
                result = await response.json()
                if result is None:
                    result = dict()
                result['_headers'] = response.headers
                return result
            except Exception as e:
                logger.error(
                    "Failed to decode JSON from response text"
                    " '%s' (%s)", await response.text(), e)
                raise
        else:
            return response
    return wrapper


@pytest.fixture
def create_user_request(make_request):
    async def wrapper(user_data, expected_status=None, client=None):
        return await make_request(
            'dvhb_hybrid.users:create', json=user_data, client=client, expected_status=expected_status)
    return wrapper


@pytest.fixture
def login_request(make_request):
    async def wrapper(user_data, expected_status=None, client=None):
        return await make_request(
            'dvhb_hybrid.user:login', json=user_data, client=client, expected_status=expected_status)
    return wrapper


@pytest.fixture
def logout_request(make_request):
    async def wrapper(expected_status=None, client=None):
        return await make_request('dvhb_hybrid.user:logout', client=client, expected_status=expected_status)
    return wrapper


@pytest.fixture
def get_activation_code(app):
    async def wrapper(email):
        activation_request = await app.m.user_activation_request.get_by_email(email)
        if activation_request:
            return activation_request.code
    return wrapper


@pytest.fixture
def user():
    return {
        'email': 'user@example.com',
        'password': 'password',
    }


@pytest.fixture
def new_user_data():
    return {
        'email': '{}@example.com'.format(uuid4()),
        'password': 'Pa55w0rd',
        'g-recaptcha-response': ''
    }


@pytest.fixture
def create_new_user(app, new_user_data):
    async def wrapper():
        user = await app.models.user.create(
            email=new_user_data['email'], password=make_password(new_user_data['password']), is_active=True)
        result = dict(new_user_data)
        result['id'] = user.id
        return result
    return wrapper


@pytest.fixture
def get_user(app):
    async def wrapper(user_id=None, email=None):
        assert user_id or email
        if user_id:
            return await app.models.user.get_one(user_id)
        else:
            return await app.models.user.get_one(app.models.user.table.c.email == email)
    return wrapper


@pytest.fixture
def get_profile_request(make_request):
    async def wrapper(expected_status=None, client=None):
        return await make_request(
            'dvhb_hybrid.user:profile',
            method='get',
            client=client,
            expected_status=expected_status)
    return wrapper
