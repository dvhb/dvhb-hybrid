import os
from glob import glob

import aiohttp_jinja2
import yaml


def load_all(app, path):
    fs = glob(os.path.join(path, '*/mail.yml'))
    fs += glob(os.path.join(path, '*/mail.yaml'))
    result = {}
    for f in fs:
        with open(f) as fd:
            result.update(yaml.load(fd))

    for k, v in result.items():
        for part, body in v.items():
            v[part] = get_template(app, body)

    return result


class FormatRender:
    def __init__(self, app, template):
        self.app = app
        self.template = template

    def render(self, **kwargs):
        return self.template.format(**kwargs)


def get_template(app, data):
    if isinstance(data, str):
        return FormatRender(app, data)

    elif not isinstance(data, dict):
        raise NotImplementedError()

    elif 'template' in data:
        env = aiohttp_jinja2.get_env(app)
        return env.get_template(data['template'])
