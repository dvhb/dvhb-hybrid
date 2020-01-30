import asyncio
import functools
from weakref import WeakKeyDictionary

from .debug import ConnectionLogger
from ..utils import get_app_from_parameters, get_context_from_parameters


class Guard:
    tasks = {}

    def __init__(self, key, loop):
        self._key = key
        self._task = asyncio.Task.current_task(loop=loop)
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
                context = get_context_from_parameters(*args, **kwargs)
                with Guard('pg', context.loop):
                    # db is predefined key for postgres in context
                    async with context.db.acquire() as connection:
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
