def redis_key(project_slug, key, namespace=None):
    return '{}:{}:{}'.format(
        project_slug,
        namespace.replace('/', ':'),
        key)


class RedisMixin:
    project_slug = None

    @classmethod
    def redis_key(cls, key, namespace=None):
        return redis_key(cls.project_slug, key, namespace=namespace)

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
