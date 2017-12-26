from dvhb_hybrid import utils
from dvhb_hybrid.amodels import Model, method_connect_once
from .enums import UserActionLogEntryType, UserActionLogEntrySubType


class BaseUserActionLogEntry(Model):
    """
    Abstract action log entry async model class
    """

    @classmethod
    def get_table_from_django(cls, django_model):
        return super().get_table_from_django(django_model, 'payload')

    @classmethod
    def set_defaults(cls, data: dict):
        data.setdefault('created_at', utils.now())

    @classmethod
    @method_connect_once
    async def create_record(
            cls, request, message, type, subtype, payload=None, user_id=None, object=None, connection=None):
        rec_data = await cls._prepare_data(
            request, message, type, subtype, payload, user_id, object, connection=connection)
        return await cls.create(**rec_data, connection=connection)

    @classmethod
    async def _prepare_data(cls, request, message, type, subtype, payload, user_id, object, connection):
        rec_data = dict(
            ip_address=None,
            message=message,
            user_id=user_id,
            type=type.value,
            subtype=subtype.value,
            payload=payload,
            content_type_id=None,
            object_id=None,
            object_repr=None,
        )
        if request is not None:
            peername = request.transport.get_extra_info('peername')
            if peername is not None:
                rec_data['ip_address'], _ = peername
            if hasattr(request, 'user') and rec_data['user_id'] is None:
                rec_data['user_id'] = request.user.id
        if object is not None:
            rec_data['object_id'] = str(object.pk)
            rec_data['object_repr'] = repr(object)
            rec_data['content_type_id'] = 28
        return rec_data

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

    @classmethod
    @method_connect_once
    async def create_user_create_model(
            cls, request, model_name, connection=None):
        return await cls.create_record(
            request,
            message="User created new '{}'".format(model_name),
            type=UserActionLogEntryType.crud,
            subtype=UserActionLogEntrySubType.create,
            connection=connection)

    @classmethod
    @method_connect_once
    async def create_user_update_model(
            cls, request, model_name, connection=None):
        return await cls.create_record(
            request,
            message="User updated '{}'".format(model_name),
            type=UserActionLogEntryType.crud,
            subtype=UserActionLogEntrySubType.update,
            connection=connection)

    @classmethod
    @method_connect_once
    async def create_user_delete_model(
            cls, request, model_name, connection=None):
        return await cls.create_record(
            request,
            message="User deleted '{}'".format(model_name),
            type=UserActionLogEntryType.crud,
            subtype=UserActionLogEntrySubType.delete,
            connection=connection)
