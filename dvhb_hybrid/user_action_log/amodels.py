from dvhb_hybrid import utils
from dvhb_hybrid.amodels import Model, method_connect_once
from . import models
from .enums import UserActionLogEntryType, UserActionLogEntrySubType


class UserActionLogEntry(Model):
    table = Model.get_table_from_django(models.UserActionLogEntry, "payload")

    @classmethod
    def set_defaults(cls, data: dict):
        data.setdefault('created_at', utils.now())

    @classmethod
    @method_connect_once
    async def create_record(cls, request, message, type, subtype, payload=None, connection=None):
        user_id = None
        ip_address = None
        if request is not None:
            peername = request.transport.get_extra_info('peername')
            if peername is not None:
                ip_address, _ = peername
            if request.user:
                user_id = request.user.id
        return await cls.create(
            user_id=user_id, ip_address=ip_address, message=message, type=type.value, subtype=subtype.value,
            payload=payload, connection=connection)

    @classmethod
    @method_connect_once
    async def create_login(cls, request, connection=None):
        return await cls.create_record(
            request,
            message="User logged in",
            type=UserActionLogEntryType.auth,
            subtype=UserActionLogEntrySubType.login,
            connection=connection)

    @classmethod
    @method_connect_once
    async def create_logout(cls, request, connection=None):
        return await cls.create_record(
            request,
            message="User logged out",
            type=UserActionLogEntryType.auth,
            subtype=UserActionLogEntrySubType.logout,
            connection=connection)
