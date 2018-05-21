import importlib
import pkgutil
import functools
import hashlib
import json
import os
import re
import time
import uuid
import zlib

import aiohttp
from django.utils import timezone

from .aviews import JsonEncoder

r_uuid4 = (r'[a-f0-9]{8}-?'
           r'[a-f0-9]{4}-?'
           r'4[a-f0-9]{3}-?'
           r'[89ab][a-f0-9]{3}-?'
           r'[a-f0-9]{12}')

re_uuid4 = re.compile(r_uuid4)

re_class_name = re.compile(r'([A-Z]*[a-z]*)')


def now(ms=True, ts=False):
    if ts:
        n = time.time()
        if not ms:
            n = int(n)
    else:
        n = timezone.now()
        if not ms:
            n = n.replace(microsecond=0)
    return n


def get_uuid4(s, match=True):
    if match:
        m = re_uuid4.match(s)
    else:
        m = re_uuid4.search(s)
    if not m:
        return
    return uuid.UUID(m.group(0))


def get_hash(data: str) -> str:
    return str(abs(zlib.crc32(data.encode())))


def import_module_from_all_apps(apps_path, module):
    """Imports all the modules from apps directory"""
    # Импортируем "module" из всех приложений.
    for dir_name in os.listdir(apps_path):
        package_dir = os.path.join(apps_path, dir_name)
        if os.path.isdir(package_dir):
            init = os.path.join(package_dir, '__init__.py')
            if not os.path.exists(init) or os.path.isdir(init):
                continue
            try:
                importlib.import_module('{}.{}'.format(dir_name, module))
            except ImportError:
                pass


def import_modules_from_packages(package, module):
    """Imports all the apps from package"""
    for importer, modname, ispkg in pkgutil.iter_modules(package.__path__):
        if ispkg:
            try:
                importlib.import_module('{}.{}.{}'.format(package.__name__, modname, module))
            except ImportError:
                pass


def convert_class_name(name):
    """
    >>> convert_class_name('ClassName')
    'class_name'
    >>> convert_class_name('ABClassName')
    'abclass_name'
    """
    l = re_class_name.findall(name)
    return '_'.join(i.lower() for i in l if i)


def int_or_zero(v):
    """
    Convert object to int
    """
    if isinstance(v, str):
        v = v.strip()
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def enum_to_choice(v):
    translation = v.translation() if hasattr(v, 'translation') else {}
    return [
        (a.value, translation.get(a, a.name))
        for a in v
    ]


def hash_data(data):
    """
    >>> hash_data({'h': 123, 'f': 43})
    'fcc217e2223b1291abf6e58a6e656bfd'
    >>> hash_data({'f': 43, 'h': 123})
    'fcc217e2223b1291abf6e58a6e656bfd'
    >>> hash_data(['h', 43])
    'e2de391295334b9b27272e6517ed047a'
    """
    m = hashlib.md5()
    m.update(json.dumps(
        data, sort_keys=True, cls=JsonEncoder,
    ).encode())
    return m.hexdigest()


def import_class(py_path):
    path, class_name = py_path.rsplit('.', 1)
    module = importlib.import_module(path)
    return getattr(module, class_name)


def method_client_once(func):
    @functools.wraps(func)
    async def wraper(self, *args, **kwargs):
        if kwargs.get('client') is None:
            with aiohttp.ClientSession() as client:
                kwargs['client'] = client
                return await func(self, *args, **kwargs)
        else:
            return await func(self, *args, **kwargs)
    return wraper


def _merge(a, b, path=None):
    """merges b into a"""
    if path is None:
        path = []
    for key, bv in b.items():
        if key in a:
            av = a[key]
            nested_path = path + [key]
            if isinstance(av, dict) and isinstance(bv, dict):
                _merge(av, bv, nested_path)
                continue
        a[key] = bv
    return a


def merge(*args, **kwargs):
    args = ({},) + args + (kwargs,)
    return functools.reduce(_merge, args)


def query_bool(data):
    if data in (True, 'true', 'True', 1, '1', 'yes', 'on'):
        return True
    elif data in (False, 'false', 'False', 0, '0', 'no', 'off'):
        return False


def get_app_from_parameters(*args, **kwargs):
    if kwargs.get('request') is not None:
        return kwargs['request'].app
    for i in args:
        if hasattr(i, 'app'):
            return i.app
        elif hasattr(i, 'request'):
            return i.request.app
        elif hasattr(i, '_context'):
            return i._context.app
