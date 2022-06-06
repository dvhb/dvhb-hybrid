import pytest

from .conftest import PROVIDER_PARAMS, PROVIDERS_TO_TEST


@pytest.mark.django_db
async def test_oauth_redirect_unknown_provider(oauth_redirect_request):
    await oauth_redirect_request(provider_name='xxx', expected_status=400)


@pytest.mark.django_db
async def test_oauth_redirect_provider_not_configured(oauth_redirect_request):
    await oauth_redirect_request(provider_name='google', expected_status=404)


@pytest.mark.django_db
@pytest.mark.parametrize('provider', PROVIDERS_TO_TEST)
async def test_oauth_redirect_successful(provider, oauth_redirect_request, config):
    response = await oauth_redirect_request(provider_name=provider, expected_status=302)
    location = response.headers['Location']
    assert location.startswith(PROVIDER_PARAMS[provider]['auth_url'])
    assert config.social[provider]['client_id'] in location
    assert 'response_type=code' in location
