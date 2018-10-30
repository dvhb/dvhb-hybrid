import uuid

import aioredis
from aiohttp import web

from dvhb_hybrid import sitemap


async def redis_close(app):
    pool = app['redis']
    pool.close()
    await pool.wait_closed()


async def test_sitemap(loop, test_client, mocker):
    app = web.Application(loop=loop)
    app.config = mocker.Mock()
    app.config.redis.default.prefix = 'dvhb_hybrid:test'

    app['redis'] = await aioredis.create_redis_pool(('localhost', 6379), loop=loop)
    app.on_shutdown.append(redis_close)

    def sitemap_handler(request):
        return sitemap.sitemap(request, key=str(uuid.uuid4()), data={
            '/test': {
                'priority': 1,
            }
        })

    app.router.add_get('/test', sitemap_handler)
    client = await test_client(app)
    response = await client.get('/test')
    assert response.status == 200
