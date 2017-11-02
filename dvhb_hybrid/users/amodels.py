import random
import string
import uuid

from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string
from dvhb_hybrid import utils
from dvhb_hybrid.amodels import Model, method_connect_once

from .enums import UserConfirmationRequestStatus


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

    # Fields to be included into user profile data
    user_profile_fields = (
        'email',
        'first_name',
        'last_name',
        'is_staff',
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

    @method_connect_once
    async def get_profile(self, connection=None):
        profile_data = dict()
        for f in self.user_profile_fields:
            profile_data[f] = getattr(self, f)
        if self.picture:
            profile_data['picture'] = self.picture
        self.prepare_image(profile_data)
        return profile_data

    @method_connect_once
    async def patch_profile(self, profile_data, connection=None):
        need_update = []
        for f in self.user_profile_fields:
            if f in profile_data:
                setattr(self, f, profile_data[f])
                need_update.append(f)

        if need_update:
            await self.save(fields=need_update, connection=connection)

    def prepare_image(self, result=None):
        if not self.get('picture'):
            return
        if result is None:
            result = self
        result['picture_uuid'] = utils.get_uuid4(self.picture, match=False)
        for k, v in (
                ('picture_150', 'hybrid.files:image:processor'),
                ('picture_150_2x', 'hybrid.files:image_2x:processor')):
            result[k] = self.app.router[v].url_for(
                uuid=result['picture_uuid'],
                processor='size',
                width=150, height=150,
                ext='jpg')


class BaseAbstractConfirmationRequest(Model):
    primary_key = 'uuid'

    @classmethod
    def set_defaults(cls, data: dict):
        data.setdefault('uuid', uuid.uuid4())
        data.setdefault('created_at', utils.now())
        data.setdefault('status', UserConfirmationRequestStatus.sent.value)
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

    def is_confirmed(self):
        return self.status == UserConfirmationRequestStatus.confirmed.value

    def is_cancelled(self):
        return self.status == UserConfirmationRequestStatus.cancelled.value

    @method_connect_once
    async def confirm(self, connection=None):
        self.status = UserConfirmationRequestStatus.confirmed.value
        await self.save(fields=['status', 'updated_at'], connection=connection)

    @method_connect_once
    async def cancel(self, connection=None):
        self.status = UserConfirmationRequestStatus.cancelled.value
        await self.save(fields=['status', 'updated_at'], connection=connection)

    @method_connect_once
    async def mark_as_sent(self, connection=None):
        self.status = UserConfirmationRequestStatus.sent.value
        await self.save(fields=['status', 'updated_at'], connection=connection)

    @classmethod
    @method_connect_once
    async def send(cls, user, lang_code, connection=None):
        """
        Sends email with profile deletion request confirmation to the user specified
        """

        confirmation_request = await cls.create(
            email=user.email, user_id=user.pk, lang_code=lang_code, connection=connection)
        await cls.app.mailer.send(
            user.email,
            template=cls.template_name,
            context = cls.get_template_context(confirmation_request),
            lang_code = confirmation_request.lang_code)
        return confirmation_request


class AbstractUserActivationRequest(BaseAbstractConfirmationRequest):

    template_name = 'AccountActivation'

    @classmethod
    def get_template_context(cls, confirmation_request):
        activation_url = cls.app.config.users.url_template.format(activation_code=confirmation_request.code)
        return dict(url=activation_url)


class AbstractUserProfileDeleteRequest(BaseAbstractConfirmationRequest):

    template_name = 'AccountRemovingConfirmation'

    @classmethod
    def get_template_context(cls, confirmation_request):
        confirm_url = cls.app.config.users.confirm_delete_url_template.format(
            confirmation_code=confirmation_request.code)
        cancel_url = cls.app.config.users.cancel_delete_url_template.format(
            confirmation_code=confirmation_request.code)
        return dict(
            confirm_url=confirm_url,
            cancel_url=cancel_url
        )
