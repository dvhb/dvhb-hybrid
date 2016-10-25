import os

import invoke
import yaml


def load_conf(overrides=None, *, base_path, env_path, env_prefix, user_prefix, system_prefix):
    with open(base_path) as f:
        base = yaml.load(f)
    path = os.environ.get(env_path)
    if not overrides and path and os.path.isfile(path):
        with open(path) as f:
            overrides = yaml.load(f)
    return invoke.Config(
        defaults=base,
        overrides=overrides,
        system_prefix=system_prefix,
        user_prefix=user_prefix,
        env_prefix=env_prefix,
    )


def absdir(directory, base_dir):
    if not directory.startswith('/'):
        directory = os.path.join(base_dir, directory)
    return os.path.normpath(directory)


def dirs(list_dir, base_dir):
    result = []
    for i in list_dir:
        result.append(absdir(i, base_dir))
    return result
