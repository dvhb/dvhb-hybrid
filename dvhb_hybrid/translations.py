import os
from collections import Sequence

from babel.support import Translations as BaseTranslations


class Translations(BaseTranslations):
    def __call__(self, msg, msg_plural=None, count=None):
        if msg_plural is not None:
            assert count is not None
            return self.ungettext(msg, msg_plural, count)
        else:
            return self.ugettext(msg)


def load_translations(root, domain):
    result = {}
    for i in os.listdir(root):
        if not os.path.isdir(os.path.join(root, i)):
            continue
        result[i] = Translations.load(root, [i], domain)
        lang = i.split('_')[0]
        if lang != i:
            result[lang] = result[i]
    return result


class Localizer:
    def __init__(self, lang):
        self.lang = lang

    def __call__(self, obj):
        if isinstance(obj, Sequence):
            for i in obj:
                i.localize(i, self.lang)
        else:
            obj.localize(obj, self.lang)
