from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from dvhb_hybrid.models import UpdatedMixin
from dvhb_hybrid.utils import enum_to_choice

from .enums import UserActivationRequestStatus


class AbstractUserManager(BaseUserManager):
    """
    User manager supporting email address as username
    """

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_("Email address is required"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True'))

        return self._create_user(email, password, **extra_fields)


class AbstractUser(AbstractBaseUser, PermissionsMixin):
    class Meta:
        db_table = 'users_user'
        verbose_name = _('user')
        verbose_name_plural = _('users')

    email = models.EmailField(_('email'), max_length=255, unique=True, null=True)
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can '
                    'log into this admin site.')
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )

    date_joined = models.DateTimeField(_('registration date'), default=timezone.now)
    date_deleted = models.DateTimeField(_('removing date'), null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = AbstractUserManager()

    def get_short_name(self):
        return self.first_name


class UserActivationRequest(UpdatedMixin, models.Model):
    uuid = models.UUIDField(_('UUID'), primary_key=True)
    email = models.EmailField(verbose_name=_('email'), max_length=255)
    user = models.ForeignKey('users.AbstractUser', related_name='+', verbose_name=_('user'))
    status = models.CharField(verbose_name=_('status'), max_length=20,
                              choices=enum_to_choice(UserActivationRequestStatus),
                              default=UserActivationRequestStatus.sent.value)

    class Meta:
        verbose_name = _('user activation request')
        verbose_name_plural = _('user activation requests')
