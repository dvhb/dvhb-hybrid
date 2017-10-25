import pytest


@pytest.mark.django_db
async def test_create_user_empty_data(create_user_request):
    status, data = await create_user_request({})
    assert status == 400


@pytest.mark.django_db
async def test_create_user_successful(create_user_request, new_user_data):
    status, data = await create_user_request(new_user_data)
    assert status == 200
