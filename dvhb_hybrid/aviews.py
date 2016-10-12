import datetime
import functools
import json
import uuid

from aiohttp import web
from aiohttp_apiset.views import ApiSet


class JsonEncoder(json.JSONEncoder):
    ensure_ascii = False

    @classmethod
    def dumps(cls, data, **kwargs):
        kwargs.setdefault('ensure_ascii', cls.ensure_ascii)
        return json.dumps(
            data, cls=cls, **kwargs
        )

    def default(self, o):
        if isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, uuid.UUID):
            return str(o)
        elif isinstance(o, (map, set, frozenset)):
            return list(o)
        else:
            return super(JsonEncoder, self).default(o)


dumper = functools.partial(
    json.dumps, ensure_ascii=False, cls=JsonEncoder)


class BaseView(ApiSet):
    default_response = 'json2'
    limit_body = None

    @property
    def app(self):
        return self.request.app

    @classmethod
    def redis_key(cls, key, namespace=None):
        namespace = namespace or cls.namespace
        return 'vprs:{}:{}'.format(namespace.replace('/', ':'), key)

    @classmethod
    async def redis(cls, request, key, *, value=None, sadd=None, expire=None,
                    default=None, namespace=None, smembers=False, srem=None,
                    delete=False, connection=None):
        key = cls.redis_key(key, namespace=namespace)

        async def _redis(cache):
            if value:
                await cache.set(key, value)
            elif delete:
                await cache.delete(key)
            elif sadd:
                if isinstance(sadd, (list, tuple)):
                    await cache.sadd(key, *sadd)
                else:
                    await cache.sadd(key, sadd)
            elif smembers:
                v = await cache.smembers(key)
                return v or default
            elif srem:
                return await cache.srem(key, srem)
            elif not expire:
                return (await cache.get(key)) or default
            if expire:
                await cache.expire(key, int(expire))

        if connection is not None:
            return await _redis(connection)
        else:
            async with request.app.redis.get() as connection:
                return await _redis(connection)

    @classmethod
    def response_json2(cls, data, **kwargs):
        return web.json_response(data, dumps=dumper)

    def check_size_body(self, request, limit=None):
        limit = limit or self.limit_body
        if not limit:
            return
        elif not request.content_length:
            raise self.response(status=411)
        elif request.content_length > limit:
            raise self.response(status=413)

    def list_params(self, data: dict, limit=10, offset=0):
        try:
            limit = int(data.get('limit'))
            if not 1 <= limit < 1000:  # LIMIT
                raise ValueError()
        except (ValueError, TypeError):
            pass
        try:
            offset = int(data.get('offset'))
            if not 0 <= offset:
                raise ValueError()
        except (ValueError, TypeError):
            pass
        return limit, offset


def response_file(url, mime_type):
    raise web.HTTPOk(
        content_type=mime_type,
        headers={
            'X-Accel-Redirect': url,
        },
    )


async def http200(request):
    raise web.HTTPOk(body=b'')
