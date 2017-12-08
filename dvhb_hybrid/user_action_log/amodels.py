from dvhb_hybrid import utils
from dvhb_hybrid.amodels import Model, method_connect_once
from . import models


class UserActionLogEntry(Model):
    table = Model.get_table_from_django(models.UserActionLogEntry, "payload")

    @classmethod
    def set_defaults(cls, data: dict):
        data.setdefault('created_at', utils.now())
