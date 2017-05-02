from aiohttp_apiset.swagger.operations import OperationIdMapping

from . import amodels, image  # noqa

opid = OperationIdMapping(image)

default_app_config = 'dvhb_hybrid.files.apps.FilesConfig'
