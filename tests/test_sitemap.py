import uuid

import pytest

from dvhb_hybrid import sitemap

from .conftest import Conf


@pytest.fixture
def config(config):
    c = Conf()
    c.load_plugins(force=True)
    config.load_yaml("""
    app:
      cleanup_ctx:
        redis: dvhb_hybrid.config.cleanup_ctx_redis
    redis:
      default: {}
    """)
    return config


@pytest.mark.django_db
async def test_sitemap(app, aiohttp_client):

    def sitemap_handler(request):
        return sitemap.sitemap(request, key=str(uuid.uuid4()), data={
            '/test': {
                'priority': 1,
            }
        })

    app.router.add_get('/test', sitemap_handler)
    client = await aiohttp_client(app)
    response = await client.get('/test')
    assert response.status == 200
