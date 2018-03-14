import logging

from babel import Locale


logger = logging.getLogger(__name__)


class LocaleMiddleware:
    def __init__(self, default_locale, translations):
        if not isinstance(default_locale, Locale):
            default_locale = Locale.parse(default_locale)
        if default_locale.language not in translations:
            raise KeyError('There are no translations for default locale %s' % default_locale)
        self._default_locale = default_locale
        self._translations = translations

    async def __call__(self, app, next_handler):
        async def handler(request):
            locale = self._detect_locale(request)
            translations = self._lookup_translations(locale)
            request['locale'] = locale
            request['gettext'] = translations
            return await next_handler(request)
        return handler

    def _lookup_translations(self, locale):
        key = '%s_%s' % (locale.language, locale.territory)
        result = self._translations.get(key)
        if not result:
            result = self._translations.get(locale.language)
        if not result:
            result = self._translations[self._default_locale.language]
        return result

    def _detect_locale(self, request):
        locale = _parse_accept_language(request.headers.get('accept-language'))
        if locale:
            try:
                return Locale.parse(locale)
            except Exception as exc:
                logger.warning(
                    'Failed to parse locale: %s (locale=%r), '
                    'falling back to default',
                    exc,
                    locale
                )
        return self._default_locale


def _parse_accept_language(lang):
    if not lang:
        return
    locales = []
    for i in lang.split(","):
        i = i.strip().split(";")
        if len(i) > 1 and i[1].startswith("q="):
            try:
                score = float(i[1][2:])
            except (ValueError, TypeError):
                score = 0.0
        else:
            score = 1.0
        locales.append((i[0], score))
    if locales:
        locales.sort(key=lambda x: x[1], reverse=True)
        return locales[0][0].replace('-', '_')
