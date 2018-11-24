import random
import string
import uuid

from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string

from .. import utils
from ..amodels import Model, method_connect_once
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
        data.setdefault('is_active', False)
        data.setdefault('is_superuser', False)
        data.setdefault('is_staff', False)
        data.setdefault('first_name', '')
        data.setdefault('last_name', '')

        if 'password' not in data:
            password = ''.join(random.sample(string.ascii_letters + string.digits, 10))
            data['password'] = make_password(password)

    @classmethod
    @method_connect_once
    def get_user_by_email(cls, email, *, silent=True, connection=None):
        return cls.get_one(cls.table.c.email == email, connection=connection, silent=silent)

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

    @classmethod
    @method_connect_once
    async def change_email(cls, user_id, new_email_address, connection=None):
        user = await cls.get_one(user_id, connection=connection)
        user.email = new_email_address
        await user.save(fields=['email'], connection=connection)

    @method_connect_once
    async def on_login(self, connection=None):
        # Update login timestamp
        self.last_login = utils.now()
        await self.save(fields=['last_login'], connection=connection)

    @classmethod
    @method_connect_once
    async def get_by_oauth_provider(cls, provider, uid, connection=None):
        try:
            c_oauth_info = cls.table.c.oauth_info
        except AttributeError as e:
            msg = "User model has no column '%s'. It seems that UserOAuthMixin should be enabled" % e
            raise AttributeError(msg) from e
        where = [
            c_oauth_info['provider'].astext == provider,
            c_oauth_info['id'].astext == str(uid)
        ]
        return await cls.get_one(*where, connection=connection, silent=True)

    @method_connect_once
    async def save_oauth_info(self, provider, uid, connection=None):
        await self.update_json(oauth_info={provider: uid}, connection=connection)

    def __repr__(self):
        return \
            "{self.__class__.__name__}(" \
            "id={self.id}, " \
            "email='{self.email}')"\
            .format(self=self)


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

    @method_connect_once
    async def send_via_mailer(self, connection=None):
        context = self.get_template_context()
        context['http_hostname'] = self.app.config.hostname
        await self.app.mailer.send(
            self.email,
            template=self.template_name,
            context=context,
            lang_code=self.lang_code, db_connection=connection)

    @classmethod
    @method_connect_once
    async def send(cls, user, lang_code, connection=None):
        """
        Send confirmation request to user email address using translation of class message template into language given
        """

        confirmation_request = await cls.create(
            email=user.email, user_id=user.pk, lang_code=lang_code, connection=connection)
        await confirmation_request.send_via_mailer(connection=connection)
        return confirmation_request

    def get_status(self):
        "Returns confirmation request status string representation"

        return UserConfirmationRequestStatus(self.status).name


class AbstractUserActivationRequest(BaseAbstractConfirmationRequest):

    template_name = 'AccountActivation'

    def get_template_context(self):
        activation_url = self.app.config.users.url_template.format(activation_code=self.code)
        return dict(
            url=activation_url)


class AbstractUserProfileDeleteRequest(BaseAbstractConfirmationRequest):

    template_name = 'AccountRemovingConfirmation'

    def get_template_context(self):
        confirm_url = self.app.config.users.confirm_delete_url_template.format(confirmation_code=self.code)
        cancel_url = self.app.config.users.cancel_delete_url_template.format(confirmation_code=self.code)
        return dict(
            confirm_url=confirm_url,
            cancel_url=cancel_url
        )


class AbstractUserChangeEmailOriginalAddressRequest(BaseAbstractConfirmationRequest):

    template_name = 'EmailChangeForOriginalAddress'

    def get_template_context(self):
        confirm_url = self.app.config.users.confirm_email_change_url_template.format(confirmation_code=self.code)
        return dict(
            confirm_url=confirm_url,
            orig_email=self.orig_email,
            new_email=self.new_email,
        )

    @classmethod
    @method_connect_once
    async def get_by_new_email(cls, new_email_address, user_id=None, connection=None):
        args = [cls.table.c.new_email == new_email_address]
        if user_id:
            args.append(cls.table.c.user_id == user_id)
        return await cls.get_one(*args, connection=connection, silent=True)

    @classmethod
    @method_connect_once
    async def send(cls, user, new_email_address, lang_code, connection=None):
        """
        Sends email with email change request to the original email address of user specified
        """

        confirmation_request = await cls.create(
            email=user.email, orig_email=user.email, new_email=new_email_address, user_id=user.pk,
            lang_code=lang_code, connection=connection)
        await confirmation_request.send_via_mailer(connection=connection)
        return confirmation_request


class AbstractUserChangeEmailNewAddressRequest(AbstractUserChangeEmailOriginalAddressRequest):

    template_name = 'EmailChangeForNewAddress'

    @classmethod
    @method_connect_once
    async def send(cls, user, new_email_address, lang_code, connection=None):
        """
        Sends email with email change request to the new email address
        """

        confirmation_request = await cls.create(
            email=new_email_address, orig_email=user.email, new_email=new_email_address, user_id=user.pk,
            lang_code=lang_code, connection=connection)
        await confirmation_request.send_via_mailer(connection=connection)
        return confirmation_request
