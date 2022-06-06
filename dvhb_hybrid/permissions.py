import functools
import uuid

from dvhb_hybrid import exceptions, utils
from dvhb_hybrid.redis import redis_key


def get_api_key(request):
    return (
        request.headers.get('API-KEY') or
        request.headers.get('Authorization') or
        request.query.get('api_key')
    )


async def get_session_data(request, sessions=None):
    api_key = get_api_key(request)
    request.api_key = api_key
    session = {}
    if api_key:
        try:
            api_key = str(uuid.UUID(api_key))
        except (ValueError, TypeError):
            pass
        else:
            d = await sessions.hgetall(redis_key(request.app.name, api_key, 'session'))
            session = {k.decode(): v.decode() for k, v in d.items()}
    request.session = session
    return session


async def get_current_user(request, *,
                           anonymous_allowed=True,
                           sessions=None,
                           connection=None,
                           fields=None):
    if hasattr(request, 'user'):
        return request.user

    data = await get_session_data(request, sessions=sessions)
    if not data:
        raise exceptions.HTTPUnauthorized()

    user_id = data.get('uid')
    if not user_id:
        if not anonymous_allowed:
            raise exceptions.HTTPUnauthorized(reason='anonymous not allowed')
        request.user = request.app.models.user()
        request.user.is_active = True
        return request.user

    user = await request.app.models.user.get_one(
        int(user_id),
        connection=connection,
        fields=fields,
        silent=True
    )
    if not user:
        raise exceptions.HTTPUnauthorized()

    request.user = user
    return user


def get_request_from_args(args, kwargs):
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
    return request


def permissions(view=None, *, is_superuser=False):
    def wrapper_outer(view):
        @functools.wraps(view)
        async def wrapper(*args, **kwargs):
            request = get_request_from_args(args, kwargs)
            user = await get_current_user(request, connection=kwargs.get('connection'))
            if is_superuser and not user.is_superuser:
                raise exceptions.HTTPUnauthorized(reason='Not a superuser')
            return await view(*args, **kwargs)
        return wrapper

    # Decorator used without keyword arguments
    if view:
        return wrapper_outer(view)
    # Decorator used with keyword arguments, so view=None
    else:
        return wrapper_outer


async def gen_api_key(user_id, *, request=None, **kwargs):
    assert request is not None  # TODO: make request required
    sessions = request.app.sessions

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

    await sessions.hmset(full_key, u)

    request.api_key = api_key
    return api_key
