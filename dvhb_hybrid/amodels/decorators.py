import functools

from .debug import ConnectionLogger
from ..utils import get_app_from_parameters


def method_connect_once(arg):
    def with_arg(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if kwargs.get('connection') is None:
                app = get_app_from_parameters(*args, **kwargs)
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
                async with app[redis].get() as connection:
                    kwargs[redis] = connection
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        return wrapper

    if not callable(arg):
        redis = arg
        return with_arg

    return with_arg(arg)
