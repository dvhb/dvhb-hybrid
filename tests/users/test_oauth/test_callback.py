import pytest

from aioresponses import aioresponses
from yarl import URL

from .conftest import PROVIDERS_TO_TEST, PROVIDER_PARAMS, get_email, set_email


@pytest.mark.django_db
async def test_oauth_callback_unknown_provider(oauth_callback_request):
    await oauth_callback_request(provider_name='xxx', code='xxx', expected_status=400)


@pytest.mark.django_db
async def test_oauth_redirect_provider_not_configured(oauth_callback_request):
    await oauth_callback_request(provider_name='google', code='xxx', expected_status=404)


@pytest.fixture
def execute_callback(oauth_callback_request):
    async def wrapper(provider):
        with aioresponses(passthrough=['http://127.0.0.1']) as response_mock:
            access_token = PROVIDER_PARAMS[provider]['token']
            profile_url = URL(PROVIDER_PARAMS[provider]['profile_url']).update_query(access_token=access_token)
            profile_data = PROVIDER_PARAMS[provider]['profile_data']
            # Mock request for access token obtaining
            response_mock.post(
                PROVIDER_PARAMS[provider]['token_url'], status=200, payload=dict(access_token=access_token))
            # Mock request for user profile obtaining
            response_mock.get(profile_url, status=200, payload=profile_data)
            # Execute request with auth code
            response = await oauth_callback_request(
                provider_name=provider, code=PROVIDER_PARAMS[provider]['auth_code'], expected_status=302)
            return response.headers['Location']

    return wrapper


@pytest.mark.django_db
@pytest.mark.parametrize('provider', PROVIDERS_TO_TEST)
async def test_oauth_callback_successful(provider, app, test_client, execute_callback, config, get_user):
    await test_client(app)  # To initialize DB

    profile_data = PROVIDER_PARAMS[provider]['profile_data']
    email = get_email(profile_data)

    # User is not exist yet
    user = await get_user(email=email)
    assert user is None

    # First attempt should create and login new user
    location = await execute_callback(provider)
    # Should be redirected to login success page
    assert location == config.social['url']['success']
    user = await get_user(email=email)
    assert user.last_login is not None
    assert user['oauth_info'][provider] == profile_data['id']
    assert user.is_active  # user should be active after creation
    profile = await user.get_profile()
    assert 'first_name' in profile
    assert 'last_name' in profile

    # Second attempt should login existing user
    location = await execute_callback(provider)
    # Should be redirected to login success page
    assert location == config.social['url']['success']


@pytest.mark.django_db
async def test_oauth_callback_several_providers(app, test_client, uuid, execute_callback, get_user):
    await test_client(app)  # To initialize DB

    email = '{}@example.com'.format(uuid())

    for provider in PROVIDERS_TO_TEST:
        profile_data = PROVIDER_PARAMS[provider]['profile_data']
        set_email(profile_data, email)
        await execute_callback(provider)

    user = await get_user(email=email)
    print(user['oauth_info'])
    assert user.is_active
    for provider in PROVIDERS_TO_TEST:
        profile_data = PROVIDER_PARAMS[provider]['profile_data']
        print("Testing", provider)
        assert user['oauth_info'][provider] == profile_data['id']
