import functools
import operator
import uuid

from dvhb_hybrid import amodels, utils
from dvhb_hybrid import exceptions
from dvhb_hybrid.amodels import method_redis_once
from dvhb_hybrid.redis import redis_key


def get_api_key(request):
    return request.headers.get('API-KEY') or request.headers.get('Authorization') or request.GET.get('api_key')


async def get_session_data(request, sessions=None):
    api_key = get_api_key(request)
    request.session = api_key

    if not api_key:
        request.session_data = {}
        return request.session_data

    @amodels.method_redis_once('sessions')
    def get_data(request, sessions):
        return sessions.hgetall(redis_key(request.app.name, api_key, 'session'))

    try:
        api_key = str(uuid.UUID(api_key))
    except (ValueError, TypeError):
        return None
    else:
        d = await get_data(request, sessions=sessions)
        return {k.decode(): v.decode() for k, v in d.items()}


async def get_current_user(request, *, anonymous_allowed=True, sessions=None, connection=None, fields=None):
    data = await get_session_data(request, sessions=sessions)

    if not data:
        raise exceptions.HTTPUnauthorized()
    elif 'uid' in data:
        user_id = data['uid']
    else:
        user_id = None

    if not user_id:
        if not anonymous_allowed:
            raise exceptions.HTTPUnauthorized(reason='anonymous not allowed')
        request.user = request.app.models.user()
        request.user.is_active = True
        return request.user

    user = await request.app.models.user.get_one(
        user_id, connection=connection, fields=fields, silent=True)

    if not user:
        raise exceptions.HTTPUnauthorized()

    request.user = user
    return user


def permissions(arg):
    def with_arg(view):
        @functools.wraps(view)
        async def wrapper(*args, **kwargs):
            if 'request' in kwargs:
                request = kwargs['request']
            else:
                for arg in args:
                    if hasattr(arg, 'rel_url'):
                        request = arg
                        break
                    elif hasattr(arg, 'request'):
                        request = arg.request
                        break
                else:
                    raise NotImplementedError('request not found')
            await get_current_user(request)
            return await view(*args, **kwargs)
        return wrapper
    if not callable(arg):
        return with_arg
    return with_arg(arg)


@method_redis_once('sessions')
async def gen_api_key(user_id, *, request=None, sessions=None, **kwargs):
    if user_id:
        kwargs['uid'] = str(user_id)

    old_key = get_api_key(request)

    if old_key:
        full_key = redis_key(request.app.name, old_key, 'session')
        u = await sessions.hgetall(full_key)
        u = {
            k.decode(): v.decode()
            for k, v in u.items()
        }
        if 'uid' in u:  # not anon
            raise exceptions.HTTPConflict()
        u.update(kwargs)
        api_key = old_key
    else:
        u = kwargs
        u['c'] = utils.now(ts=True)
        api_key = str(uuid.uuid4())
        full_key = redis_key(request.app.name, api_key, 'session')

    pairs = functools.reduce(operator.add, u.items())
    await sessions.hmset(full_key, *pairs)

    request.session = api_key
    return api_key
