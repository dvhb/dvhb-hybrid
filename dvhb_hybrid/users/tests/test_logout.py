import pytest


async def logout_request(api):
    response = await api.post('user:logout')
    return response.status, await response.json()


@pytest.mark.django_db
async def test_logout_unauthorized(app, test_client):
    api = await test_client(app)
    status, _ = await logout_request(api)
    assert status == 401


@pytest.mark.django_db
async def test_logout_successful(app, test_client, user):
    api = await test_client(app)
    await api.authorize(**user)
    status, _ = await logout_request(api)
    assert status == 200
