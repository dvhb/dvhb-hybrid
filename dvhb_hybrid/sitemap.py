import asyncio
import xml.etree.cElementTree as ET

from aiohttp import web

from . import amodels


doctype = '<?xml version="1.0" encoding="UTF-8"?>'
content_type = 'application/xml'


def get_xml(request, items: dict):
    urlset = ET.Element('urlset')
    urlset.attrib['xmlns'] = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    for loc, attrs in items.items():
        url = ET.SubElement(urlset, 'url')
        ET.SubElement(url, 'loc').text = '{scheme}://{host}{loc}'.format(
            scheme=request.scheme, host=request.host, loc=loc)
        for tag, text in attrs.items():
            ET.SubElement(url, tag).text = str(text)

    return ET.tostring(urlset, encoding='unicode')


@amodels.method_redis_once
async def sitemap(request, redis, *, key, data):
    prefix = request.app.context.config.redis.default.get('prefix')
    if prefix:
        key = ':'.join([prefix, 'sitemap', key])
    else:
        key = ':'.join(['sitemap', key])

    body = await redis.get(key)
    if body:
        return web.Response(body=body, content_type=content_type)

    if asyncio.iscoroutine(data):
        data = await data
    body = get_xml(request, data)
    body = '\n'.join([doctype, body])
    await redis.set(key, body)
    await redis.expire(key, 3600)
    return web.Response(text=body, content_type=content_type)


# Example
# sitemap.yml
# /:
#     priority: 1
#     changefreq: hourly
#
# /about:
#     priority: 0.4
#     changefreq: weekly
#
# with open(os.path.join(BASE_DIR, 'project', 'settings', 'sitemap.yml')) as f:
#     root_data = yaml.load(f)
#
#
# def root(request):
#     return sitemap(request, key='root', data=root_data)
