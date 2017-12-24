import enum

from django.utils.translation import ugettext_lazy as _


class UserActionLogEntryType(enum.Enum):
    reg = 'reg'
    auth = 'auth'
    crud = 'crud'
    email = 'email'

    @classmethod
    def translation(cls):
        return {
            cls.reg: _('User registration'),
            cls.auth: _('User authentification'),
            cls.crud: _('CRUD'),
            cls.email: _('Email'),
        }


class UserActionLogEntrySubType(enum.Enum):
    create = 'create'
    update = 'update'
    delete = 'delete'
    login = 'login'
    logout = 'logout'
    change_password = 'change_password'

    @classmethod
    def translation(cls):
        return {
            cls.create: _('Created'),
            cls.update: _('Changed'),
            cls.delete: _('Deleted'),
            cls.login: _('Login'),
            cls.logout: _('Logout'),
            cls.change_password: _('Change password'),
        }
