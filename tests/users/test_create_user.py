import pytest


@pytest.mark.django_db
async def test_create_user_empty_data(create_user_request):
    await create_user_request({}, expected_status=400)


@pytest.mark.django_db
async def test_create_user_successful_default_lang_code(create_user_request, new_user_data):
    await create_user_request(new_user_data, expected_status=200)


@pytest.mark.django_db
async def test_create_user_successful_with_lang_code(create_user_request, new_user_data):
    new_user_data['lang_code'] = 'fr'
    await create_user_request(new_user_data, expected_status=200)
