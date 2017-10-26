from uuid import uuid4

import pytest


@pytest.fixture
def create_user_request(app, test_client):
    async def wrapper(user_data, api=None):
        api = api or await test_client(app)
        response = await api.post('dvhb_hybrid.users:create', json=user_data)
        return response.status, await response.json()
    return wrapper


@pytest.fixture
def login_request(app, test_client):
    async def wrapper(user_data, api=None):
        api = api or await test_client(app)
        response = await api.post(api.token_url, json=user_data)
        return response.status, await response.json()
    return wrapper


@pytest.fixture
def logout_request(app, test_client):
    async def wrapper(api=None):
        api = api or await test_client(app)
        response = await api.post('dvhb_hybrid.user:logout')
        return response.status, await response.json()
    return wrapper


@pytest.fixture
def get_activation_code(app):
    async def wrapper(email):
        activation_request = await app.m.user_activation_request.get_by_email(email)
        if activation_request:
            return activation_request.code
    return wrapper


@pytest.fixture
def new_user_data():
    return {
        'email': '{}@example.com'.format(uuid4()),
        'password': 'Pa55w0rd',
        'g-recaptcha-response': ''
    }
