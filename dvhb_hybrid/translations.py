import os

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
