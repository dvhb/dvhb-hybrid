from aiohttp.web_exceptions import HTTPOk


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
    async def check_status(result, response=HTTPOk):
        assert result.status == response.status_code, await result.text()

    @staticmethod
    async def prepare_result(r):
        data = None
        if 'application/json' in r.headers['Content-Type']:
            data = await r.json()
        return r, data
