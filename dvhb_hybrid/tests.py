import json

import pytest
from aiohttp import ClientSession, hdrs, test_utils, web


class BaseTestApi:
    """Base class to test API"""
    API_KEY = 'API-KEY'

    def __init__(self, client, user):
        self.client = client
        self.app = client.server.app
        self.user = user
        self.headers = {'content-type': 'application/json'}

    def get_route(self, name):
        name = name if name.startswith(self.app.name) else '{}.{}'.format(self.app.name, name)
        return self.app.router[name]

    @staticmethod
    async def check_status(result, response=web.HTTPOk):
        assert result.status == response.status_code, await result.text()

    @staticmethod
    async def prepare_result(r):
        data = None
        if 'application/json' in r.headers['Content-Type']:
            data = await r.json()
        return r, data


class TestClient(test_utils.TestClient):
    base_path = None

    def dumps(self, data):
        return json.dumps(data)

    def request(
            self, method, path, *args,
            parts=None, json=None,
            **kwargs):
        # support name as url
        if isinstance(path, str):
            if not path.startswith('/'):
                parts = parts or {}
                path = self.server.app.router[path].url_for(**parts)
            elif self.base_path and not path.startswith(self.base_path):
                path = self.base_path + path
        # support raw data
        if json is not None:
            kwargs['data'] = self.dumps(json)
            hs = kwargs.setdefault('headers', {})
            hs[hdrs.CONTENT_TYPE] = 'application/json'
        return super().request(
            method=method, path=path, *args, **kwargs)


class AuthClient(TestClient):
    token_url = 'dvhb_hybrid.user:login'
    default_user = {
        'email': 'test_user@example.com',
        'password': '123',
    }

    @property
    def user_model(self):
        return self.server.app.m.user

    async def ensure_user(self, **kwargs):
        pass

    async def authorize(self, **kwargs):
        for k, v in self.default_user.items():
            kwargs.setdefault(k, v)
        await self.ensure_user(**kwargs)
        response = await self.post(self.token_url, json=kwargs)
        assert response.status == web.HTTPOk.status_code, await response.text()
        await self.set_auth_session(response)

    async def set_auth_session(self, response):
        auth = hdrs.AUTHORIZATION
        headers = {auth: response.headers[auth]}
        self._session = ClientSession(headers=headers, loop=self._loop)


@pytest.yield_fixture
def test_client(loop, client_class):
    """Factory to create a TestClient instance.
    test_client(app, **kwargs)
    """
    clients = []

    async def go(app, server_kwargs=None, **kwargs):
        if isinstance(app, web.Application):
            server_kwargs = server_kwargs or {}
            server = test_utils.TestServer(app, loop=loop, **server_kwargs)
        else:
            server = app
        client = client_class(server, loop=loop, **kwargs)
        await client.start_server()
        clients.append(client)
        return client

    yield go

    async def finalize():
        while clients:
            await clients.pop().close()

    loop.run_until_complete(finalize())
