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
    async def create_record(cls, request, message, type, subtype, payload=None, user_id=None, connection=None):
        ip_address = None
        if request is not None:
            peername = request.transport.get_extra_info('peername')
            if peername is not None:
                ip_address, _ = peername
            if hasattr(request, 'user') and user_id is None:
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

    @classmethod
    @method_connect_once
    async def create_change_password(cls, request, connection=None):
        return await cls.create_record(
            request,
            message="User changed password",
            type=UserActionLogEntryType.auth,
            subtype=UserActionLogEntrySubType.change_password,
            connection=connection)

    @classmethod
    @method_connect_once
    async def create_user_registration(cls, request, connection=None):
        return await cls.create_record(
            request,
            message="User registered",
            type=UserActionLogEntryType.reg,
            subtype=UserActionLogEntrySubType.create,
            connection=connection)

    @classmethod
    @method_connect_once
    async def create_user_deletion(cls, request, connection=None):
        return await cls.create_record(
            request,
            message="User deleted",
            type=UserActionLogEntryType.reg,
            subtype=UserActionLogEntrySubType.delete,
            connection=connection)

    @classmethod
    @method_connect_once
    async def create_user_profile_update(cls, request, connection=None):
        return await cls.create_record(
            request,
            message="User updated profile",
            type=UserActionLogEntryType.reg,
            subtype=UserActionLogEntrySubType.update,
            connection=connection)

    @classmethod
    @method_connect_once
    async def create_user_change_email_address(
            cls, request, user_id, old_email, new_email, confirmation_code, connection=None):
        return await cls.create_record(
            request,
            message="User changed email address",
            type=UserActionLogEntryType.email,
            subtype=UserActionLogEntrySubType.update,
            payload=dict(old_email=old_email, new_email=new_email, confirmation_code=confirmation_code),
            user_id=user_id,
            connection=connection)
