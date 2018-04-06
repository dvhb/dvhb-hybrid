import aiopg.sa
from aioworkers.http import Application
from aiohttp_apiset import SwaggerRouter

import dvhb_hybrid
import tests
from dvhb_hybrid.amodels import AppModels


class Application(Application):
    def __init__(self, **kwargs):
        kwargs['debug'] = kwargs['config'].debug
        router = SwaggerRouter()
        kwargs.setdefault('client_max_size', 2 ** 25)
        super().__init__(router=router, **kwargs)
        router.set_cors(self)

        self.models = self.m = AppModels(self)

        cls = type(self)
        self.on_startup.append(cls.startup_database)
        self.on_cleanup.append(cls.cleanup_database)
        self.on_response_prepare.append(self.on_prepare)

    async def startup_database(self):
        dbparams = self.config.databases.default
        self['db'] = await aiopg.sa.create_engine(**dbparams, loop=self.loop)
        AppModels.import_all_models_from_packages(dvhb_hybrid)
        AppModels.import_all_models_from_packages(tests)
        self.models = self.m = AppModels(self)

    async def cleanup_database(self):
        async with self['db']:
            pass

    async def on_prepare(self, request, response):
        if request.path.startswith('/api'):
            # This disables caching in IE, see
            response.headers['Cache-Control'] = 'no-cache'

    @property
    def name(self):
        return self.config.app.name

    @property
    def db(self):
        return self.get('db')
