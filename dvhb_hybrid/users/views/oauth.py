import aioauth_client
from aiohttp.web_exceptions import HTTPNotFound, HTTPFound
from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from yarl import URL

from dvhb_hybrid.amodels import method_connect_once
from dvhb_hybrid.permissions import gen_api_key

# Prevent limiting data to fields defined in aioauth_client.User
aioauth_client.User = lambda **kwargs: kwargs


class UserOAuthView:

    @property
    def model(self):
        return self.request.app.m.user

    async def _on_login_successful(self, user):
        conf = self.request.app.config.social
        await gen_api_key(user.id, request=self.request)
        url = URL(conf.url.success).with_query(api_key=self.request.session)
        # Redirect to our login success page
        raise HTTPFound(url)

    @method_connect_once
    async def oauth_handler(self, request, provider, access_token=None, connection=None):
        conf = request.app.config.social
        if provider not in conf:
            return HTTPNotFound(reason="OAuth provider not configured")

        # Initialize OAuth2 client
        Client = aioauth_client.ClientRegistry.clients[provider]
        client = Client(**conf[provider], access_token=access_token)
        client.params['redirect_uri'] = str(request.url.with_query(''))
        provider_data = {}

        if not access_token:
            # No authorization code found in query
            if client.shared_key not in request.query:
                # Redirect to provider's authorization page
                return HTTPFound(client.get_authorize_url())
            elif 'error' in request.query:
                # Redirect to our reject page
                url = URL(conf.url.reject).with_query(request.query)
                return HTTPFound(url)
            else:
                # Request access token from provider
                _, provider_data = await client.get_access_token(request.GET)

        # Obtain user profile data from provider
        user_info, raw_data = await client.user_info()

        if not user_info.get('email'):
            user_info['email'] = provider_data.get('email')

        # Try to find user in DB by provider ID
        user = await self.model.get_by_oauth_provider(provider, user_info['id'])
        if user is not None:
            # User need to be activated
            if not user.is_active:
                # Redirect to our activation page
                return HTTPFound(conf.url.need_activate)
            else:
                await self._on_login_successful(user)

        # No email address obtained
        if not user_info.get('email'):
            # Redirect to our registration page
            url = URL(conf.url.reg).with_query(user_info)
            return HTTPFound(url)

        # Try to find user by email address
        user = await self.model.get_user_by_email(user_info['email'])

        if user is not None:
            if not user.is_active:
                return HTTPFound(conf.url.need_activate)
        else:
            user = self.model(email=user_info['email'])
            user['password'] = make_password(get_random_string())
            self.model.set_defaults(user)
            await user.save()

        await user.save_oauth_info(provider, user_info['id'], connection=connection)
        await user.patch_profile(user_info, connection=connection)

        await self._on_login_successful(user)
