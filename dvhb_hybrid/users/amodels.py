import random
import string
import uuid

from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from dvhb_hybrid import utils
from dvhb_hybrid.amodels import Model, method_connect_once

from .enums import UserActivationRequestStatus, UserProfileDeleteRequestStatus


class AbstractUser(Model):

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

    @method_connect_once
    async def delete_account(self, connection=None):
        self.date_deleted = utils.now()
        self.is_active = False
        # Add random string to email to allow new registration with such address
        self.email = '#'.join((self.email[:230], get_random_string()))
        await self.save(fields=['email', 'date_deleted', 'is_active'], connection=connection)


class AbstractUserActivationRequest(Model):
    primary_key = 'uuid'

    @classmethod
    def set_defaults(cls, data: dict):
        data.setdefault('uuid', uuid.uuid4())
        data.setdefault('created_at', utils.now())
        data.setdefault('status', UserActivationRequestStatus.sent.value)
        data['updated_at'] = utils.now()

    @property
    def code(self):
        """
        Returns string representation of UUID without dashes
        """

        return str(self.uuid).replace('-', '')

    @classmethod
    @method_connect_once
    async def send(cls, user, connection=None):
        """
        Sends email with activation request to the user specified
        """

        activation = await cls.create(
            email=user.email, user_id=user.pk, lang_code=user.get('lang_code', 'en'), connection=connection)
        context = dict(
            url=cls.app.config.users.url_template.format(activation_code=activation.code)
        )
        await cls.app.mailer.send(
            user.email,
            template='AccountActivation',
            context = context,
            lang_code = activation.lang_code)

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


class AbstractUserProfileDeleteRequest(Model):
    primary_key = 'uuid'

    @classmethod
    def set_defaults(cls, data: dict):
        data.setdefault('uuid', uuid.uuid4())
        data.setdefault('created_at', utils.now())
        data.setdefault('status', UserProfileDeleteRequestStatus.created.value)
        data['updated_at'] = utils.now()

    @property
    def code(self):
        """
        Returns string representation of UUID without dashes
        """

        return str(self.uuid).replace('-', '')

    @classmethod
    @method_connect_once
    def get_by_email(cls, email, connection=None):
        return cls.get_one(cls.table.c.email == email, connection=connection, silent=True)

    @classmethod
    @method_connect_once
    async def send(cls, user, lang_code, connection=None):
        """
        Sends email with profile deletion request confirmation to the user specified
        """

        deletion_request = await cls.create(
            email=user.email, user_id=user.pk, lang_code=lang_code, connection=connection)
        context = dict(
            confirm_url=cls.app.config.users.confirm_delete_url_template.format(
                confirmation_code=deletion_request.code),
            cancel_url=cls.app.config.users.cancel_delete_url_template.format(
                confirmation_code=deletion_request.code)
        )
        await cls.app.mailer.send(
            user.email,
            template='AccountRemovingConfirmation',
            context = context,
            lang_code = deletion_request.lang_code)
        return deletion_request

    def is_confirmed(self):
        return self.status == UserProfileDeleteRequestStatus.confirmed.value

    def is_cancelled(self):
        return self.status == UserProfileDeleteRequestStatus.cancelled.value

    @method_connect_once
    async def confirm(self, connection=None):
        self.status = UserProfileDeleteRequestStatus.confirmed.value
        await self.save(fields=['status', 'updated_at'], connection=connection)

    @method_connect_once
    async def cancel(self, connection=None):
        self.status = UserProfileDeleteRequestStatus.cancelled.value
        await self.save(fields=['status', 'updated_at'], connection=connection)

    @method_connect_once
    async def mark_as_sent(self, connection=None):
        self.status = UserProfileDeleteRequestStatus.sent.value
        await self.save(fields=['status', 'updated_at'], connection=connection)
