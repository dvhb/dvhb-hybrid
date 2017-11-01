import pytest


@pytest.fixture
def user_deletion_request(make_request):
    async def wrapper(expected_status=None, client=None):
        return await make_request(
            'dvhb_hybrid.user:request_deletion', client=client, expected_status=expected_status)
    return wrapper


@pytest.fixture
def confirm_deletion_request(make_request):
    async def wrapper(code, expected_status=None, client=None):
        return await make_request(
            'dvhb_hybrid.user:confirm_deletion',
            json=dict(confirmation_code=code),
            client=client,
            expected_status=expected_status)
    return wrapper


@pytest.fixture
def cancel_deletion_request(make_request):
    async def wrapper(code, expected_status=None, client=None):
        return await make_request(
            'dvhb_hybrid.user:cancel_deletion',
            json=dict(confirmation_code=code),
            client=client,
            expected_status=expected_status)
    return wrapper


@pytest.fixture
def get_deletion_request(app):
    async def wrapper(email):
        return await app.m.user_profile_delete_request.get_by_email(email)
    return wrapper


@pytest.mark.django_db
async def test_request_user_deletion_not_authorized(user_deletion_request):
    await user_deletion_request(expected_status=401)


@pytest.mark.django_db
async def test_confirm_not_authorized(confirm_deletion_request):
    await confirm_deletion_request(code='F' * 32, expected_status=401)


@pytest.mark.django_db
async def test_cancel_not_authorized(cancel_deletion_request):
    await cancel_deletion_request(code='F' * 32, expected_status=401)


@pytest.mark.django_db
async def test_confirm_unknown_code(app, test_client, user, confirm_deletion_request):
    client = await test_client(app)
    await client.authorize(**user)
    await confirm_deletion_request(code='F' * 32, client=client, expected_status=404)


@pytest.mark.django_db
async def test_cancel_unknown_code(app, test_client, user, cancel_deletion_request):
    client = await test_client(app)
    await client.authorize(**user)
    await cancel_deletion_request(code='F' * 32, client=client, expected_status=404)


@pytest.mark.django_db
async def test_request_user_deletion_successful1(
        app, test_client, create_new_user, user_deletion_request, get_deletion_request, confirm_deletion_request):
    client = await test_client(app)
    user = await create_new_user()
    await client.authorize(email=user['email'], password=user['password'])
    await user_deletion_request(client=client, expected_status=200)
    req = await get_deletion_request(user['email'])
    await confirm_deletion_request(code=req.code, client=client, expected_status=200)
    req = await get_deletion_request(user['email'])
    assert req.is_confirmed()


@pytest.mark.django_db
async def test_request_user_deletion_successful2(
        app, test_client, create_new_user, user_deletion_request, get_deletion_request, cancel_deletion_request):
    client = await test_client(app)
    user = await create_new_user()
    await client.authorize(email=user['email'], password=user['password'])
    await user_deletion_request(client=client, expected_status=200)
    req = await get_deletion_request(user['email'])
    await cancel_deletion_request(code=req.code, client=client, expected_status=200)
    req = await get_deletion_request(user['email'])
    assert req.is_cancelled()
