import pytest


@pytest.mark.django_db
async def test_logout_unauthorized(logout_request):
    status, _ = await logout_request()
    assert status == 401


@pytest.mark.django_db
async def test_logout_successful(app, test_client, logout_request, user):
    api = await test_client(app)
    await api.authorize(**user)
    status, _ = await logout_request(api=api)
    assert status == 200