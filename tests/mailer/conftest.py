import pytest


@pytest.fixture
def config(config):
    config.load_yaml("""
    mailer:
      autorun: true
      persist: true
      from_email: hybrid@dvhb.io
      django_email_backend_params:
        host: smtp.dvhb.io
      cls: dvhb_hybrid.mailer.django.Mailer
      django_email_backend: django.core.mail.backends.locmem.EmailBackend
      templates_from_module: dvhb_hybrid
    models:
      mailer:
        func: dvhb_hybrid.utils.import_class
        args: [dvhb_hybrid.mailer.amodels.Message]
    """)
    return config
