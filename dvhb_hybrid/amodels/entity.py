import importlib
import logging
import pkgutil
import sys

from aioworkers.core.base import AbstractEntity

from . import Model

logger = logging.getLogger(__name__)


class ContextModels(AbstractEntity):
    def __init__(self, config=None, *, context=None, loop=None):
        super().__init__(config, context=context, loop=loop)
        self.db = None
        self.redis = None
        self._module = self.config.get('module', 'amodels')
        self._search_models()

    async def init(self):
        # Models require postgres and redis
        self.db = self.context[self.config.get('db', 'db')]
        self.redis = self.context[self.config.get('redis', 'redis')]

    def _search_models(self):
        """
        Search for models in specified package
        """
        package = sys.modules[self.config.package]
        for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
            if ispkg:
                try:
                    m = '{}.{}.{}'.format(package.__name__, modname, self._module)
                    importlib.import_module(m)
                    logger.info(f"Load module {m}")
                except ImportError:
                    pass

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        return KeyError(item)

    def __getattr__(self, item):
        if item in Model.models:
            model_cls = Model.models[item]
            sub_class = model_cls.factory(context=self.context)
            setattr(self, item, sub_class)
            if hasattr(model_cls, 'relationships'):
                for k, v in model_cls.relationships.items():
                    setattr(sub_class, k, v(app=self.context.app, context=self.context))
            return sub_class
        raise AttributeError('%r has no attribute %r' % (self, item))
