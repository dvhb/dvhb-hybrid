import os
import re
from abc import ABC, abstractmethod
from collections import ChainMap
from glob import glob
from typing import Any, Mapping, Optional

import aiohttp_jinja2
import attr
import jinja2
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
    def render(self, context: Mapping[str, Any], **kwargs) -> str:
        pass


class FormatRender(Render):
    def __init__(self, template):
        self.template = template

    def render(self, context=None, **kwargs):
        ctx = self.get_context(context, kwargs)
        return self.template.format_map(ctx)


class Jinja2Render(Render):
    def __init__(
        self, *,
        from_string=None,
        template_name=None,
        app=None,
        env=None,
    ):
        if env is not None:
            self._env = env
        elif app is not None:
            self._env = aiohttp_jinja2.get_env(app)
        else:
            self._env = None
        if from_string:
            self.template = self._env.from_string(from_string)
        elif self._env:
            self.template = self._env.get_template(template_name)
        else:
            raise ValueError()

    def render(self, context=None, **kwargs):
        ctx = self.get_context(context, kwargs)
        return self.template.render(ctx)


def get_template(app, data):
    if isinstance(data, str):
        return FormatRender(data)

    elif not isinstance(data, dict):
        raise NotImplementedError()

    elif 'template' in data:
        env = aiohttp_jinja2.get_env(app)
        return env.get_template(data['template'])


class TemplateRender(Render):
    re_img = re.compile(r'(<img.*? src=["\'])\.*/(.*?["\'].*?>)', re.I | re.U)

    def __init__(self, template: jinja2.Template, cache: dict) -> None:
        self._template = template
        self._cache = cache

    def render(self, context=None, **kwargs):
        ctx = self.get_context(context, kwargs)
        if ctx == self._cache.get('ctx'):
            return self._cache['render']
        result = self._template.render(ctx)
        self._cache['ctx'] = ctx
        email_url = ctx.get('email_url')
        if email_url:
            result = self.re_img.sub(
                r'\g<1>' + email_url + r'\g<2>', result
            )
        self._cache['render'] = result
        return result


class TitleTemplateRender(TemplateRender):
    re_title = re.compile(r'<title>(.*?)</title>', re.I | re.U)

    def render(self, context=None, **kwargs):
        html = super().render(context, **kwargs)
        m = self.re_title.search(html)
        if m:
            return m.group(1)
        return ''


@attr.s(auto_attribs=True)
class EmailTemplate:
    subject: Render
    body: Render
    html: Optional[Render]

    @classmethod
    def create_from_jinja2(
        cls, template: jinja2.Template,
    ) -> 'EmailTemplate':
        cache = {}
        return cls(
            subject=TitleTemplateRender(template, cache=cache),
            body=FormatRender(''),
            html=TemplateRender(template, cache=cache)
        )

    @classmethod
    def create_from_str(cls, subject, body, html=None, env=None):
        if isinstance(subject, str):
            subject = FormatRender(subject)
        else:
            raise TypeError('Unsupported type {} for subject'
                            ''.format(type(body)))
        if isinstance(body, str):
            body = FormatRender(body)
        else:
            raise TypeError('Unsupported type {} for body'
                            ''.format(type(body)))
        if isinstance(html, str):
            html = Jinja2Render(from_string=html, env=env)
        return cls(subject=subject, body=body, html=html)
