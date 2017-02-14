Tutorial
========

You can use this tutorial to start new project or integrate aiohttp application to your Django project.

Start project
-------------

Start you project using `django-admin startproject` command:

.. code-block:: shell

    $ mkdir tutorial
    $ cd tutorial
    $ pyvenv venv
    $ . venv/bin/activate
    $ pip install django
    $ django-admin startproject tutorial .

Project structure will be look like this:

.. code-block:: none

    tutorial/
    ├── manage.py
    ├── tutorial
    │   ├── __init__.py
    │   ├── settings.py
    │   ├── urls.py
    │   └── wsgi.py
    └── venv

Install dvhb-hybrid:

.. code-block:: shell

    $ pip install git+https://github.com/dvhbru/dvhb-hybrid

Create an application
---------------------

Generally Django project consist of few application.

For instance we need to create a method GET /users which will return a list of users in the application.
To do this we need to create `users` django application and place it as subpackage of `tutorial` package:

.. code-block:: shell

    $ mkdir tutorial/users
    $ django-admin startapp users tutorial/users

Now we can declare `User` model in `users/models.py` by extending `django.contrib.auth.models.AbstractUser`:

.. code-block:: python

    from django.contrib.auth.models import AbstractUser


    class User(AbstractUser):
        pass


To access this model from asyncio code we need to create a `tutorial/users/amodels.py`
and add there a `User` class by extending `dvhb_hybrid.amodels.Model`.
This model will be loaded by `dvhb_hybrid.amodels.AppModels` and used to access the data from async functions.

.. code-block:: python

    from dvhb_hybrid.amodels import Model

    from .models import User as DjangoUser

    class User(Model):
        # Create SQLAlchemy table based on Django table
        table = Model.get_table_from_django(DjangoUser)


Let's add an async function which will be used our model in module `tutorial/users/views.py`:

.. code-block:: python

    async def get_users(request):
	    return await request.app.m.user.get_list(fields=['username', 'email'])



Our aiohttp application uses `SwaggerRouter` from `aiohttp_apiset` to build application router and we need to specify
our endpoint as swagger spec here `tutorial/users/users_api.yaml`:

.. code-block:: yaml

    paths:
      '':
        get:
          $handler: tutorial.users.views.get_users
          tags:
          - user
          summary: Users list
          description: Returns list of users

          produces:
          - application/json

          responses:
            200:
            description: OK

Configuring of project
----------------------

You can configure project any way you like.
But we suggest to use common config for you Django Admin and aiohttp application.
It allow you to avoid duplication of parameters.

For instance application can be configured using `load_conf` function from `dvhb-hybrid`. It is based on `invoke.Config`.
Create a `config.yaml` in the base folder and specify database configuration:

.. code-block:: yaml

    databases:
      default:
        database: tutorial

Load configuration to `settings.py` and use it to build Django `DATABASES`:

.. code-block:: python

    from dvhb_hybrid.config import load_conf, db_to_settings

    ...

    PROJECT_SLUG = 'TUTORIAL'
    config = load_conf(
        base_path=os.path.join(BASE_DIR, 'config.yaml'),
        env_path=PROJECT_SLUG + '_CONF',
        system_prefix='/etc/tutorial',
        env_prefix=PROJECT_SLUG,
    )

    ...

    DATABASES = db_to_settings(config.databases.config, BASE_DIR)

Add our `users` application to `settings.py`:

.. code-block:: python

    ...

    INSTALLED_APPS = [
        'tutorial.users',
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
    ]

    AUTH_USER_MODEL = 'users.User'

    ...


Create DB, make migrations and migrate it:

.. code-block:: shell

    $ createdb tutorial
    $ python manage.py makemigrations
    $ python manage.py migrate

Now you can create a super user for your application:

.. code-block:: shell

    $ python manage.py createsuperuser --username admin --email admin@example.com

Run Django Administration and login here using username and password specified in previous step:

.. code-block:: shell

    $ python manage.py runserver

Create an aiohttp application
-----------------------------

Add `tutorial/api.yaml` with specification from `users` application:

.. code-block:: yaml

    swagger: '2.0'

    basePath: /api

    info:
      title: TUTORIAL API
      version: '1.0'
      description: API версии 1.0

    paths:
      /users:
      - $include: users/users_api.yaml

Create `tutorial/app.py`:

.. code-block:: python

    import os

    import django
    import aiopg.sa
    from aiohttp import web
    from aiohttp_apiset import SwaggerRouter
    from aiohttp_apiset.middlewares import jsonify
    from dvhb_hybrid.amodels import AppModels

    from .settings import config

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tutorial.settings")
    django.setup()

    # looking for amodels.py in subpackages of tutorial
    import tutorial
    AppModels.import_all_models_from_packages(tutorial)


    class Application(web.Application):
        def __init__(self, *args, **kwargs):
            # collect swagger specs in tutorial folder
            router = SwaggerRouter(search_dirs=['tutorial'], default_validate=True)
            kwargs['router'] = router
            self.config = config

            kwargs.setdefault('middlewares', []).append(jsonify)

            super().__init__(**kwargs)

            router.include('api.yaml')

            cls = type(self)
            self.on_startup.append(cls.startup_database)
            self.on_cleanup.append(cls.cleanup_database)


        async def startup_database(self):
            dbparams = self.config.databases.default.config
            self['db'] = await aiopg.sa.create_engine(**dbparams)
            # bind AppModels to the application
            self.models = self.m = AppModels(self)

        async def cleanup_database(self):
            self['db'].close()
            await self['db'].wait_closed()



Let's create `tutorial/__main__.py` as a entrypoint of the application:

.. code-block:: python

    from aiohttp import web
    from .app import Application

    def main():
        app = Application()
        web.run_app(app)

    main()

So now we can run an application:

.. code-block:: shell

    $ python -m tutorial

.. code-block:: shell

    $ curl -X GET http://localhost:8080/api/users
    [{"username": "admin", "email": "admin@example.com"}]

Final project structure will be look like this:

.. code-block:: none

    tutorial/
    ├── config.yaml
    ├── manage.py
    ├── tutorial
    │   ├── __init__.py
    │   ├── __main__.py
    │   ├── api.yaml
    │   ├── app.py
    │   ├── settings.py
    │   ├── urls.py
    │   ├── users
    │   │   ├── __init__.py
    │   │   ├── admin.py
    │   │   ├── amodels.py
    │   │   ├── apps.py
    │   │   ├── migrations
    │   │   │   ├── 0001_initial.py
    │   │   │   ├── __init__.py
    │   │   ├── models.py
    │   │   ├── tests.py
    │   │   ├── users_api.yaml
    │   │   └── views.py
    │   └── wsgi.py