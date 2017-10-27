import pytest


@pytest.fixture
def change_password_request(make_request):
    async def wrapper(old_password, new_password, expected_status=None, api=None):
        data = dict(old_password=old_password, new_password=new_password)
        return await make_request(
            'dvhb_hybrid.user:change_password', json=data, api=api, expected_status=expected_status)
    return wrapper


@pytest.mark.django_db
async def test_change_password_not_authorized(change_password_request):
    await change_password_request(old_password='xxx', new_password='yyy', expected_status=401)


@pytest.mark.django_db
async def test_change_password_wrong_old_password(app, test_client, user, change_password_request):
    api = await test_client(app)
    await api.authorize(**user)
    await change_password_request(old_password='xxx', new_password='yyy', api=api, expected_status=400)


@pytest.mark.django_db
async def test_change_password_successful(app, test_client, user, change_password_request):
    api = await test_client(app)
    user['email'] = 'user_to_change_pw@example.com'
    await api.authorize(**user)
    await change_password_request(old_password=user['password'], new_password='xxx', api=api, expected_status=200)
