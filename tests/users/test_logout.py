import pytest


@pytest.mark.django_db
async def test_logout_unauthorized(logout_request):
    await logout_request(expected_status=401)


@pytest.mark.django_db
async def test_logout_successful(app, test_client, logout_request, user):
    api = await test_client(app)
    await api.authorize(**user)
    await logout_request(api=api, expected_status=200)
