from django.contrib import admin

from . import models
from .base_admin import BaseUserActionLogEntryAdmin


@admin.register(models.UserActionLogEntry)
class UserActionLogEntryAdmin(BaseUserActionLogEntryAdmin):
    """
    Concrete action log entry admin class to be used when utilizing hybrid's user_action_log app
    """

    pass
