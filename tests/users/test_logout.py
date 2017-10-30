import pytest


@pytest.mark.django_db
async def test_logout_unauthorized(logout_request):
    await logout_request(expected_status=401)


@pytest.mark.django_db
async def test_logout_successful(app, test_client, logout_request, user):
    client = await test_client(app)
    await client.authorize(**user)
    await logout_request(client=client, expected_status=200)
