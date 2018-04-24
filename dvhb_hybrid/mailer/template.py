import os
from abc import ABC, abstractmethod
from collections import ChainMap, Mapping
from glob import glob

import aiohttp_jinja2
import yaml
from jinja2 import TemplateNotFound  # noqa


def load_all(app, path):
    fs = glob(os.path.join(path, '*/mail.yml'))
    fs += glob(os.path.join(path, '*/mail.yaml'))
    result = {}
    for f in fs:
        with open(f, encoding='utf-8') as fd:
            result.update(yaml.load(fd))

    for k, v in result.items():
        for part, body in v.items():
            v[part] = get_template(app, body)

    return result


class Render(ABC):
    def get_context(self, *maps, **kwargs):
        context = ChainMap()
        for m in maps:
            if not m:
                continue
            elif not isinstance(m, Mapping):
                raise TypeError(
                    'context should be mapping, not {}'.format(type(context)))
            context = context.new_child(m)
        return context.new_child(kwargs)

    @abstractmethod
    def render(self, context=None, **kwargs):
        pass


class FormatRender(Render):
    def __init__(self, app, template):
        self.app = app
        self.template = template

    def render(self, context=None, **kwargs):
        ctx = self.get_context(context, kwargs)
        return self.template.format_map(ctx)


class Jinja2Render(Render):
    def __init__(self, app, *, template_name=None, from_string=None):
        self.app = app
        env = app[aiohttp_jinja2.APP_KEY]
        if from_string:
            self.template = env.from_string(from_string)
        else:
            self.template = env.get_template(template_name)

    def render(self, context=None, **kwargs):
        ctx = self.get_context(context, kwargs)
        return self.template.render(ctx)


def get_template(app, data):
    if isinstance(data, str):
        return FormatRender(app, data)

    elif not isinstance(data, dict):
        raise NotImplementedError()

    elif 'template' in data:
        env = aiohttp_jinja2.get_env(app)
        return env.get_template(data['template'])
