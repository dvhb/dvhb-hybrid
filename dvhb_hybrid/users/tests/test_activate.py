import pytest


@pytest.fixture
def activate_code_request(app, test_client):
    async def wrapper(code, api=None):
        api = api or await test_client(app)
        response = await api.post('dvhb_hybrid.user:activate', json=dict(activation_code=code))
        return response.status, await response.json()
    return wrapper


@pytest.mark.django_db
async def test_activate_unknown_code(activate_code_request):
    status, _ = await activate_code_request(code='F' * 32)
    assert status == 404


@pytest.mark.django_db
async def test_activate_successful(create_user_request, new_user_data, get_activation_code, activate_code_request):
    status, _ = await create_user_request(new_user_data)
    assert status == 200

    # Extract user's activation code from the DB
    code = await get_activation_code(new_user_data['email'])
    # Activate user account using the code
    status, data = await activate_code_request(code=code)
    assert status == 200
    assert 'api_key' in data

    # Try to activate with same code again
    status, data = await activate_code_request(code=code)
    assert status == 409
