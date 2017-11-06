import pytest


@pytest.fixture
def send_email_change_request(make_request):
    async def wrapper(new_email_address, expected_status=None, client=None):
        return await make_request(
            'dvhb_hybrid.user:change_email',
            method='put',
            json=dict(new_email_address=new_email_address),
            client=client,
            expected_status=expected_status)
    return wrapper


@pytest.fixture
def approve_email_change_request(make_request):
    async def wrapper(confirmation_code, expected_status=None):
        return await make_request(
            'dvhb_hybrid.user:change_email',
            method='post',
            json=dict(confirmation_code=confirmation_code),
            expected_status=expected_status)
    return wrapper


@pytest.fixture
def get_email_change_requests(app):
    async def wrapper(new_email_address):
        return (
            await app.m.user_change_email_original_address_request.get_by_new_email(new_email_address),
            await app.m.user_change_email_new_address_request.get_by_new_email(new_email_address),
        )
    return wrapper


@pytest.mark.django_db
async def test_send_email_change_request_unauthorized(send_email_change_request):
    await send_email_change_request(new_email_address='xxx@xxx.xx', expected_status=401)


@pytest.mark.django_db
async def test_send_email_change_request_same_email(app, test_client, create_new_user, send_email_change_request):
    client = await test_client(app)
    user = await create_new_user()
    await client.authorize(email=user['email'], password=user['password'])
    await send_email_change_request(new_email_address=user['email'], client=client, expected_status=400)


@pytest.mark.django_db
async def test_send_email_change_request_successful(
        app, test_client, create_new_user, send_email_change_request, get_email_change_requests):
    client = await test_client(app)
    user = await create_new_user()
    new_email_address = 'xxx@xxx.xx'
    await client.authorize(email=user['email'], password=user['password'])
    await send_email_change_request(new_email_address=new_email_address, client=client, expected_status=200)
    orig_address_request, new_address_request = await get_email_change_requests(new_email_address)
    assert orig_address_request is not None
    assert new_address_request is not None


@pytest.mark.django_db
async def test_approve_email_change_request_invalid_code(approve_email_change_request):
    await approve_email_change_request(confirmation_code='xxx', expected_status=400)


@pytest.mark.django_db
async def test_approve_email_change_request_unknown_code(approve_email_change_request):
    await approve_email_change_request(confirmation_code='F' * 32, expected_status=404)


@pytest.mark.django_db
async def test_approve_email_change_request_successful(
        app, test_client, create_new_user, send_email_change_request, approve_email_change_request,
        get_email_change_requests, get_user):
    client = await test_client(app)
    user = await create_new_user()
    new_email_address = 'xxx@xxx.xx'
    await client.authorize(email=user['email'], password=user['password'])

    # Request email changing
    await send_email_change_request(new_email_address=new_email_address, client=client, expected_status=200)

    # Confirm both original and new address codes
    orig_address_request, new_address_request = await get_email_change_requests(new_email_address)
    await approve_email_change_request(confirmation_code=orig_address_request.code, expected_status=200)
    await approve_email_change_request(confirmation_code=new_address_request.code, expected_status=200)

    # Requests should be confirmed
    orig_address_request, new_address_request = await get_email_change_requests(new_email_address)
    assert orig_address_request.is_confirmed()
    assert new_address_request.is_confirmed()

    # User email should be changed
    user = await get_user(user_id=user['id'])
    assert user.email == new_email_address

    # Attempt to confirm same codes again
    await approve_email_change_request(confirmation_code=orig_address_request.code, expected_status=409)
    await approve_email_change_request(confirmation_code=new_address_request.code, expected_status=409)
