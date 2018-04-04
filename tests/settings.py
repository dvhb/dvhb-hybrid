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
    # 'tests'
]


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test_hybrid',
    }
}


# AUTH_USER_MODEL = 'tests.User'
SECRET_KEY = 'abc'
