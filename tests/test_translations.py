import os
import tempfile

from babel.messages import Catalog
from babel.messages.mofile import write_mo

from dvhb_hybrid.middleware.locale import LocaleMiddleware
from dvhb_hybrid.translations import load_translations


def create_locale(root, locale):
    path = os.path.join(root, locale, 'LC_MESSAGES')
    os.makedirs(path)
    catalog = Catalog(locale=locale)
    catalog.add('foo', 'bar {}'.format(locale))
    with open(os.path.join(path, 'django.mo'), 'wb') as buf:
        write_mo(buf, catalog)


async def test_middleware():
    default_locale = 'ru_RU'
    with tempfile.TemporaryDirectory(suffix='dvhb_hybrid_locales') as tmpdir:
        create_locale(tmpdir, 'ru_RU')
        create_locale(tmpdir, 'en_GB')
        translations = load_translations(tmpdir, 'django')
        assert len(translations) == 4
        m = LocaleMiddleware(default_locale, translations)
        app = object()

        async def next_handler(req):
            pass

        class Req:
            def __init__(self):
                self.data = {}
                self.headers = {}

            def __setitem__(self, item, value):
                self.data[item] = value

            def __getitem__(self, item):
                return self.data[item]

        req = Req()
        req.headers['accept-language'] = 'en-gb'
        handler = await m(app, next_handler)

        await handler(req)
        assert req['locale'].language == 'en'
        assert req['gettext'] is translations['en']
        assert req['gettext']('foo') == 'bar en_GB'

        req.headers['accept-language'] = 'ru'
        await handler(req)
        assert req['locale'].language == 'ru'
        assert req['gettext'] is translations['ru_RU']
        assert req['gettext']('foo') == 'bar ru_RU'
