class BaseTestApi:
    """Base class to test API"""
    API_KEY = 'API-KEY'

    def __init__(self, client, user):
        self.client = client
        self.user = user
        self.headers = {'content-type': 'application/json'}

    @staticmethod
    async def prepare_result(r):
        data = None
        if 'application/json' in r.headers['Content-Type']:
            data = await r.json()
        return r, data
