import pytest


@pytest.fixture
def patch_profile_request(make_request):
    async def wrapper(profile_data, expected_status=None, client=None):
        return await make_request(
            'dvhb_hybrid.user:profile',
            method='patch',
            json=profile_data,
            client=client,
            expected_status=expected_status)
    return wrapper


@pytest.mark.django_db
async def test_get_profile_unauthorized(get_profile_request):
    await get_profile_request(expected_status=401)


@pytest.mark.django_db
async def test_get_profile_successful(app, test_client, user, get_profile_request):
    client = await test_client(app)
    await client.authorize(**user)
    profile = await get_profile_request(client=client, expected_status=200)
    assert 'email' in profile


@pytest.mark.django_db
async def test_patch_profile_no_data(patch_profile_request):
    await patch_profile_request({}, expected_status=400)


@pytest.mark.django_db
async def test_patch_profile_unauthorized(patch_profile_request):
    await patch_profile_request({'xxx': 'yyy'}, expected_status=401)


@pytest.mark.django_db
async def test_patch_profile_successful(app, test_client, create_new_user, patch_profile_request):
    client = await test_client(app)
    user = await create_new_user()
    await client.authorize(email=user['email'], password=user['password'])
    new_data = {
        'first_name': 'John',
        'last_name': 'Smith',
    }
    changed_data = await patch_profile_request(new_data, client=client, expected_status=200)
    assert changed_data['first_name'] == new_data['first_name']
    assert changed_data['last_name'] == new_data['last_name']
