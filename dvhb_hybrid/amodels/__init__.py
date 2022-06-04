from .. import utils
from .convert import derive_from_django
from .decorators import method_connect_once, method_redis_once
from .model import Model
from .mptt_mixin import MPTTMixin


__all__ = [
    'AppModels',
    'Model',
    'derive_from_django',
    'method_connect_once',
    'method_redis_once',
    'MPTTMixin',
]


class AppModels:
    """
    Class to managing all models of application
    """
    def __init__(self, app):
        self.app = app

    def __getitem__(self, item):
        if hasattr(self, item):
            return getattr(self, item)
        return KeyError(item)

    def __getattr__(self, item):
        if item in Model.models:
            model_cls = Model.models[item]
            sub_class = model_cls.factory(self.app)
            setattr(self, item, sub_class)
            return sub_class
        raise AttributeError('%r has no attribute %r' % (self, item))

    @staticmethod
    def import_all_models(apps_path):
        """Imports all the models from apps_path"""
        utils.import_module_from_all_apps(apps_path, 'amodels')

    @staticmethod
    def import_all_models_from_packages(package):
        """Import all the models from package"""
        utils.import_modules_from_packages(package, 'amodels')
