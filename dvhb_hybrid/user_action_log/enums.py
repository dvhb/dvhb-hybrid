import enum

from django.utils.translation import gettext_lazy as _


class UserActionLogEntryType(enum.Enum):
    reg = 'reg'
    auth = 'auth'
    crud = 'crud'
    email = 'email'
    password = 'password'

    @classmethod
    def translation(cls):
        return {
            cls.reg: _('User registration'),
            cls.auth: _('User authentification'),
            cls.crud: _('CRUD'),
            cls.email: _('Email'),
            cls.password: _('Password'),
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


class UserActionLogStatus(enum.Enum):
    request = 'request'
    done = 'done'

    @classmethod
    def translation(cls):
        return {
            cls.request: _('Request'),
            cls.done: _('done'),
        }
