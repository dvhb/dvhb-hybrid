import pytest
from yarl import URL


@pytest.fixture
def oauth_redirect_request(app, make_request, social_conf):

    async def wrapper(provider_name, expected_status=None, configure_social=True, **kwargs):
        if configure_social:
            app.config.social = social_conf
        else:
            app.config.social = None
        return await make_request(
            'dvhb_hybrid.user:oauth:redirect', url_params=dict(provider=provider_name), url_query=kwargs, method='get',
            expected_status=expected_status, decode_json=False, allow_redirects=False)
    return wrapper


@pytest.fixture
def oauth_callback_request(app, make_request, social_conf):

    async def wrapper(provider_name, client=None, expected_status=None, configure_social=True, **kwargs):
        if configure_social:
            app.config.social = social_conf
        else:
            app.config.social = None
        return await make_request(
            'dvhb_hybrid.user:oauth:callback', client=client, method='get', expected_status=expected_status,
            decode_json=False, allow_redirects=False, url_params=dict(provider=provider_name), url_query=kwargs)
    return wrapper


@pytest.fixture
def social_conf():
    return {
        'url': {
            'success': '/',
            'reject': '/login/reject',
            'reg_oauth': '/reg/oauth',
            'reg': '/register',
            'need_activate': '/reg/activate'
        },
        'facebook': {
            'scope': 'public_profile',
            'client_id': '126306111346994',
            'client_secret': 'ffaf9c7902f8b32c184d3c68993fb9fc'
        },
        'google': {
            'scope': 'email profile',
            'client_id': '150775235058-9fmas709maee5nn053knv1heov12sh4n.apps.googleusercontent.com',
            'client_secret': 'df3JwpfRf8RIBz-9avNW8Gx7',
        },
        'vk': {
            'client_id': '5038699',
            'client_secret': 'WgKadvY82wlnleOAyw6T',
            'scope': 'offline,email'
        },
    }


PROVIDERS_TO_TEST = ['facebook', 'google']
PROVIDER_PARAMS = {
    'facebook': dict(
        auth_url='https://www.facebook.com/dialog/oauth',
        auth_code='AQAG-Iu75QfhWZ0N_hjrcF6wm9DWKrrvFB1oTQqwnRrx3OZpzmU-L4oSahS6aKnWpLhLOHT9c-HzmcBZ_GDSN-9YoW8O0mQZBJk3CiFb5Xshmy4PgomHrM9xjeblPWWcKR7WII8MJSQsPR6J1sBSSMYWNZ-IzadqkTjJl2-yWoW0QCJAyhEBAxzrlt-OPZKbUigIXTR-_c2T2ik9XbDZGwEH2MHyyjLYWqmU8zH_098qO17kExV6kTELPE3My6OvriFpCSBVaM6fxaXbSchN7821OJ5UPSBfOoghptfZDxrsX8EJpzA7nuYtlzKA2uwH2l31PHi5sFOgtuA-zg9IslYp',  # noqa
        token_url='https://graph.facebook.com/oauth/access_token',
        token='ya29.Gl17Be2cs7p1O1GnVsoSzNDo0-2z3Pb2hk7ypCKsW7vpolEswuLzl6ZCFnGIOW7v3rUqgVJShXTEopCtwUCQaFnKTxrxcqZBy4xkigS9cl9Rj_hqZtP_IAXUcjj-Jg0',  # noqa
        profile_url=URL('https://graph.facebook.com/me').with_query(fields='id,email,first_name,last_name,name,link,locale,gender,location'),  # noqa
        profile_data={
            'id': '121303115370386',
            'email': 'john_deer@yandex.ru',
            'first_name': 'John',
            'last_name': 'Deer',
            'name': 'John Deer',
            'gender': 'M',
        }),
    'google': dict(
        auth_url='https://accounts.google.com/o/oauth2/auth',
        auth_code='4/AADl81f301C0_qHriZCyyKxphdGq-psxBNcr2zMqBr3ZqkONdChRCE2GSvq0ztMQ2p8Rt_FN54lJfWRe9Lt_jHk',
        token_url='https://accounts.google.com/o/oauth2/token',
        token='ya29.Gl17Be2cs7p1O1GnVsoSzNDo0-2z3Pb2hk7ypCKsW7vpolEswuLzl6ZCFnGIOW7v3rUqgVJShXTEopCtwUCQaFnKTxrxcqZBy4xkigS9cl9Rj_hqZtP_IAXUcjj-Jg0',  # noqa
        profile_url='https://www.googleapis.com/plus/v1/people/me',
        profile_data={
            'kind': 'plus#person',
            'etag': '"EhMivDE25UysA1ltNG8tqFM2v-A/gKsUwg3FXQwI4fimtCReaZm9lc0"',
            'emails': [{'value': 'dsh@dvhb.ru', 'type': 'account'}],
            'objectType': 'person',
            'id': '101417474361894357186',
            'displayName': 'Denis Shatov',
            'name': {
                'familyName': 'Shatov',
                'givenName': 'Denis'
            },
            'image': {
                'url': 'https://lh4.googleusercontent.com/-KgDEml17-t0/AAAAAAAAAAI/AAAAAAAAAAA/HiTrlo4nT9A/photo.jpg?sz=50',  # noqa
                'isDefault': False
            },
            'isPlusUser': False,
            'language': 'en',
            'verified': False,
            'domain': 'dvhb.ru'
        }
    ),
}


def get_email(profile_data):
    try:
        return profile_data['email']
    except KeyError:
        return profile_data['emails'][0]['value']


def set_email(profile_data, email):
    if 'email' in profile_data:
        profile_data['email'] = email
    elif 'emails' in profile_data:
        profile_data['emails'][0]['value'] = email
    else:
        raise NotImplementedError
