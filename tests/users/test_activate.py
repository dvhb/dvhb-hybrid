import pytest


@pytest.fixture
def activate_code_request(make_request):
    async def wrapper(code, expected_status=None, client=None):
        return await make_request(
            'dvhb_hybrid.user:activate',
            json=dict(activation_code=code),
            client=client,
            expected_status=expected_status)
    return wrapper


@pytest.mark.django_db
async def test_activate_unknown_code(activate_code_request):
    await activate_code_request(code='F' * 32, expected_status=404)


@pytest.mark.django_db
async def test_activate_successful(create_user_request, new_user_data, get_activation_code, activate_code_request):
    await create_user_request(new_user_data, expected_status=200)

    # Extract user's activation code from the DB
    code = await get_activation_code(new_user_data['email'])
    # Activate user account using the code
    response_data = await activate_code_request(code=code, expected_status=200)
    assert 'uid' in response_data

    # Try to activate with same code again
    await activate_code_request(code=code, expected_status=409)
