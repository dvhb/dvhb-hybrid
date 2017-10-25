import random
import string
import uuid

from django.contrib.auth.hashers import make_password
from dvhb_hybrid import utils
from dvhb_hybrid.amodels import Model, method_connect_once
from sqlalchemy.dialects.postgresql import UUID

from .enums import UserActivationRequestStatus
from .models import AbstractUser as DjangoAbstractUser, UserActivationRequest as DjangoUserActivationRequest


class AbstractUser(Model):
    table = Model.get_table_from_django(DjangoAbstractUser)
    list_fields = (
        Model.primary_key,
        'email',
        'first_name',
        'last_name',
        'is_active',
        'last_login',
        'date_joined',
    )

    @classmethod
    def set_defaults(cls, data: dict):
        data.setdefault('date_joined', utils.now())
        data.setdefault('is_active', True)
        data.setdefault('is_superuser', False)
        data.setdefault('is_staff', False)
        data.setdefault('first_name', '')
        data.setdefault('last_name', '')

        if 'password' not in data:
            password = ''.join(random.sample(string.ascii_letters + string.digits, 10))
            data['password'] = make_password(password)

    @classmethod
    @method_connect_once
    def get_user_by_email(cls, email, connection=None):
        return cls.get_one(cls.table.c.email == email, connection=connection, silent=True)

    @method_connect_once
    async def activate(self, connection=None):
        self.is_active = True
        await self.save(fields=['is_active'], connection=connection)


class UserActivationRequest(Model):
    primary_key = 'uuid'
    table = Model.get_table_from_django(DjangoUserActivationRequest, uuid=UUID(as_uuid=True))

    @classmethod
    def set_defaults(cls, data: dict):
        data.setdefault('uuid', uuid.uuid4())
        data.setdefault('created_at', utils.now())
        data.setdefault('status', UserActivationRequestStatus.sent.value)
        data['updated_at'] = utils.now()

    @property
    def code(self):
        """
        Returns string representation of UUID withou dashes
        """

        return str(self.uuid).replace('-', '')

    @classmethod
    @method_connect_once
    async def send(cls, user, connection=None):
        """
        Sends email with activation request to the user specified
        """

        activation = await cls.create(email=user.email, user_id=user.pk, connection=connection)
        context = dict(
            url=cls.app.config.users.url_template.format(activation_code=activation.code)
        )
        await cls.app.mailer.send(
            user.email,
            subject='User account activation',
            body='Please follow URL {url} to activate your account',
            context=context)

    @method_connect_once
    async def activate(self, connection=None):
        self.status = UserActivationRequestStatus.activated.value
        await self.save(fields=['status', 'updated_at'], connection=connection)

    def is_activated(self):
        return self.status == UserActivationRequestStatus.activated.value

    @classmethod
    @method_connect_once
    def get_by_email(cls, email, connection=None):
        return cls.get_one(cls.table.c.email == email, connection=connection, silent=True)
