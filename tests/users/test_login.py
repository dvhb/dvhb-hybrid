import pytest


@pytest.mark.django_db
async def test_login_unknown_user(login_request, user):
    user['password'] = 'xxx'
    await login_request(user, expected_status=401)


@pytest.mark.django_db
async def test_login_disabled_user(login_request, user):
    user['email'] = 'user_disabled@example.com'
    await login_request(user, expected_status=409)


@pytest.mark.django_db
async def test_login_successful(login_request, user):
    response_data = await login_request(user, expected_status=200)
    assert 'uid' in response_data
