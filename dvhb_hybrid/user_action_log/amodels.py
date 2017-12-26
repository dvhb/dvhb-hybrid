from .base_amodels import BaseUserActionLogEntry
from . import models


class UserActionLogEntry(BaseUserActionLogEntry):
    """
    Concrete action log entry async model class to be used when utilizing hybrid's user_action_log app
    """

    table = BaseUserActionLogEntry.get_table_from_django(models.UserActionLogEntry)
