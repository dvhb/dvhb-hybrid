Tutorial
========

You can use this tutorial to start new project or integrate aiohttp application to your Django project.

Setup your environment
----------------------

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

Configuring of application
--------------------------

You can configure application any way you like.
But we suggest to use common config for you Django Admin and aiohttp applicattion in yaml file.
It allow you to avoid duplication of parameters.

Create a `config.yaml` in the project folder and specify database configuration:

.. code-block:: yaml

    databases:
      default:
        database: tutorial

Load configuration to `settings.py` and use it to build Django `DATABASE`:

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


Create DB and migrate it:

.. code-block:: shell

    $ createdb tutorial
    $ python manage.py migrate

Now you can create a user for your application via `createsuperuser` and run Django Administration:

.. code-block:: shell

    python manage.py runserver


Add aiohttp application
-----------------------

