from aiohttp_apiset.swagger.operations import OperationIdMapping

from . import amodels, image  # noqa


opid = OperationIdMapping(
    image_upload=image.image_upload,
    photo_handler_wh=image.photo_handler,
    photo_handler_wh_2x=image.photo_handler,
    photo_handler_origin_2x=image.photo_handler,
    photo_handler_origin=image.photo_handler,
    scale_to_width_or_height=image.scale_to_width_or_height,
    scale_to_width_or_height_2x=image.scale_to_width_or_height
)

default_app_config = 'dvhb_hybrid.files.apps.FilesConfig'
