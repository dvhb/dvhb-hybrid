import pytest


@pytest.fixture
def change_password_request(app, test_client):
    async def wrapper(old_password, new_password, api=None):
        api = api or await test_client(app)
        response = await api.post(
            'dvhb_hybrid.user:change_password',
            json=dict(old_password=old_password, new_password=new_password))
        return response.status, await response.json()
    return wrapper


@pytest.mark.django_db
async def test_change_password_not_authorized(change_password_request):
    status, _ = await change_password_request(old_password='xxx', new_password='yyy')
    assert status == 401


@pytest.mark.django_db
async def test_change_password_wrong_old_password(app, test_client, user, change_password_request):
    api = await test_client(app)
    await api.authorize(**user)
    status, _ = await change_password_request(old_password='xxx', new_password='yyy', api=api)
    assert status == 400


@pytest.mark.django_db
async def test_change_password_successful(app, test_client, user, change_password_request):
    api = await test_client(app)
    user['email'] = 'user_to_change_pw@example.com'
    await api.authorize(**user)
    status, _ = await change_password_request(old_password=user['password'], new_password='xxx', api=api)
    assert status == 200
