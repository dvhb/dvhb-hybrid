import os

from aioworkers.config import load_conf
from dvhb_hybrid.config import db_to_settings

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PROJECT_DIR)


configs = [
    'tests/config.yaml'
]
config = load_conf(*configs, search_dirs=[BASE_DIR])


# DATABASES = db_to_settings(config.databases, BASE_DIR)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test_dvhb_hybrid',
    }
}


INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    # 'django.contrib.sessions',
    # 'django.contrib.messages',
    # 'django.contrib.staticfiles',
    # 'django.contrib.gis',
    # 'django_admin_json_editor',
    'dvhb_hybrid.files',
    'dvhb_hybrid.mailer',
    'dvhb_hybrid.users',
    'dvhb_hybrid.user_action_log',
    'tests'
]


# AUTH_USER_MODEL = 'tests.User'
SECRET_KEY = 'abc'
