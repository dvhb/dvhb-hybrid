import os

import invoke
import yaml


def load_conf(overrides=None, local_path=None, *, base_path, env_path, system_prefix, env_prefix):
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
        env_prefix=env_prefix,
        runtime_path=local_path,
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


def convert_to_djangodb(d, name, base_dir='/tmp'):
    if d.get('database'):
        db = {
            k.upper(): v
            for k, v in d.items()
            if v}
        db['ENGINE'] = 'django.db.backends.postgresql_psycopg2'
        db['NAME'] = db.pop('DATABASE')
        # Use same db name for test. Use custom config for tests to separate test and dev dbs.
        db['TEST'] = {'NAME': db['NAME']}
    else:
        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(base_dir, name + '.sqlite3'),
        }
    return db


def db_to_settings(db_dict, base_dir):
    return {
        n: convert_to_djangodb(v, n, base_dir=base_dir)
        for n, v in db_dict.items()
    }
