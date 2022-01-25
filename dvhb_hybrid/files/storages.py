import logging
import os
from uuid import uuid4

from django.core.files.storage import FileSystemStorage
from django.utils.encoding import force_str
from django.utils.translation import ugettext_lazy as _

from .. import utils

logger = logging.getLogger(__name__)


class BaseStorage(FileSystemStorage):
    ERROR_CREATE_DIR = _('Error during creating a directory {0}')

    def create_dir(self, path):
        if not path.startswith(os.path.sep):  # is name?
            path = self.path(path)
        path = os.path.dirname(path)
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except:
            logger.exception(force_str(self.ERROR_CREATE_DIR).format(path))

    def uuid(self, name=None):
        if not name:
            return uuid4()
        return utils.get_uuid4(name, match=False)

    def mime(self, name):
        if self.exists(name):
            # TODO magic
            import magic
            mime = magic.from_file(self.path(name), mime=True)
            return force_str(mime)


class ImageStorage(BaseStorage):

    def get_name(self, name, uuid=None):
        name_uuid = self.uuid(name)
        if not uuid and name_uuid:
            uuid = name_uuid
        elif not uuid:
            uuid = uuid4()
        # elif uuid != name_uuid:
        #     name_uuid = None
        uuid = str(uuid)
        ext = os.path.splitext(name)[1].lower()
        name = os.path.join(
            'image', uuid[:2], uuid[2:4], uuid) + ext
        basename = os.path.basename(name)
        # basename = super(ImageStorage, self).get_valid_name(basename)
        return os.path.join(os.path.dirname(name), basename)

    def get_available_name(self, name, max_length=None, uuid=None):
        name = self.get_name(name, uuid)
        while self.exists(name):
            name = self.get_name(name)
        return name


image_storage = ImageStorage()
