import asyncio
import functools
from typing import Dict
from weakref import WeakKeyDictionary

from ..utils import get_app_from_parameters
from .debug import ConnectionLogger


class Guard:
    tasks: Dict[str, WeakKeyDictionary] = {}

    def __init__(self, key, loop):
        self._key = key
        self._task = asyncio.current_task(loop=loop)
        self._d = self.tasks.setdefault(key, WeakKeyDictionary())

    def __enter__(self):
        if self._task in self._d:
            raise BlockingIOError('Repeated acquire %s' % self._key)
        if self._task is not None:
            self._d[self._task] = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._task is not None:
            del self._d[self._task]


def method_connect_once(arg):
    def with_arg(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if kwargs.get('connection') is None:
                app = get_app_from_parameters(*args, **kwargs)
                with Guard('pg', app.loop):
                    async with app['db'].acquire() as connection:
                        kwargs['connection'] = ConnectionLogger(connection)
                        return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        return wrapper

    if not callable(arg):
        return with_arg
    return with_arg(arg)


def method_redis_once(arg):
    redis = 'redis'

    def with_arg(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if kwargs.get(redis) is None:
                app = get_app_from_parameters(*args, **kwargs)
                # TODO with Guard(redis, app.loop):
                kwargs[redis] = app[redis]
            return await func(*args, **kwargs)
        return wrapper

    if not callable(arg):
        redis = arg
        return with_arg

    return with_arg(arg)
