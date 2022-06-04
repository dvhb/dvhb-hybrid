import os

import aiopg.sa
import aioworkers.http
import django
from aiohttp_apiset import SwaggerRouter
from aiohttp_apiset.middlewares import jsonify

from dvhb_hybrid.amodels import AppModels


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tutorial.settings")
django.setup()

import tutorial  # noqa


AppModels.import_all_models_from_packages(tutorial)


class Application(aioworkers.http.Application):
    def __init__(self, *args, **kwargs):
        router = SwaggerRouter(search_dirs=['tutorial'])
        kwargs['router'] = router

        kwargs.setdefault('middlewares', []).append(jsonify)

        super().__init__(**kwargs)

        router.include('api.yaml')

        cls = type(self)
        self.on_startup.append(cls.startup_database)
        self.on_cleanup.append(cls.cleanup_database)

    async def startup_database(self):
        dbparams = self.config.databases.default
        self['db'] = await aiopg.sa.create_engine(**dbparams)
        self.models = self.m = AppModels(self)

    async def cleanup_database(self):
        self['db'].close()
        await self['db'].wait_closed()
