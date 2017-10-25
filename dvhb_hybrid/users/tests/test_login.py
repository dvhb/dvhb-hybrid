import pytest


@pytest.mark.django_db
async def test_login_unknown_user(login_request, user):
    user['password'] = 'xxx'
    status, _ = await login_request(user)
    assert status == 401


@pytest.mark.django_db
async def test_login_disabled_user(login_request, user):
    user['email'] = 'user_disabled@example.com'
    status, _ = await login_request(user)
    assert status == 409


@pytest.mark.django_db
async def test_login_successful(login_request, user):
    status, data = await login_request(user)
    assert status == 200
    assert 'api_key' in data
