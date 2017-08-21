import asyncio
import os
import weakref
from concurrent.futures import ProcessPoolExecutor as PoolExecutor
from uuid import UUID

import psycopg2
from aiohttp import web
from django.conf import settings

from .. import aviews
from .utils import save_image
from . import image_processors

cache = weakref.WeakValueDictionary()
resizer = PoolExecutor(max_workers=1)
image_factory = image_processors.ImageFactory()


async def image_upload(request, file):
    image_uuid = await save_image(
        request.app, request.user, file.filename,
        file.file, file.content_type)
    return {
        'uuid': image_uuid,
    }


async def get_image(request):
    request.app['state']['files_photo_db'] += 1
    Image = request.app.models.image
    async with request.app['db'].acquire() as conn:
        result = await conn.execute(
            Image.table.select()
            .where(Image.table.c.uuid == request['uuid'])
            .limit(1)
        )
        photo = await result.fetchone()

    if photo:
        request.app['state']['files_photo_db_fetch'] += 1
        return image_processors.Image(photo)


def db_error(request, error):
    request.app['state']['files_photo_db_error'] += 1
    request.app.logger.exception(error, exc_info=error)


async def get_resized_image(request, uid, w, h):
    """

    :param request:
    :param uid:
    :param w:
    :param h:
    :return: (url, mimetype)
    """
    f = cache.get(uid)
    if not f:
        f = cache[uid] = asyncio.ensure_future(get_image(request))
    if not f.done():
        request.app['state']['files_photo_db_cache_wait'] += 1
        try:
            photo = await f
        except psycopg2.DatabaseError as e:
            return db_error(request, e)
    elif f.cancelled():
        del cache[uid]
        request.app['state']['files_photo_db_cancel'] += 1
        request.app.logger.error('Cancel %s', uid)
        return
    elif f.exception():
        return db_error(request, f.exception())
    else:
        request.app['state']['files_photo_db_cache'] += 1
        photo = f.result()
    if not photo:
        return

    if w and h:
        ci = image_factory.get_generator(w, h)(source=photo)
        cachename = ci.cachefile_name
        k = cachename
        f = cache.get(k)
        if not f:
            exists = await request.app.loop.run_in_executor(
                None, os.path.exists,
                os.path.join(settings.MEDIA_ROOT, cachename)
            )
            f = cache.get(k)
            if not exists and not f:
                global resizer
                if getattr(resizer, '_broken', False):
                    request.app['state']['files_resizer_broken'] += 1
                    resizer = PoolExecutor(max_workers=1)
                request.app['state']['files_photo_resize'] += 1
                f = cache[k] = request.app.loop.run_in_executor(
                    resizer, image_factory.resize, photo.name, w, h,
                )
        if not f:
            pass
        elif not f.done():
            await f
        elif f.cancelled():
            del cache[k]
            request.app['state']['files_photo_resize_cancel'] += 1
            request.app.logger.error('Cancel %s', k)
            return
        elif f.exception():
            request.app['state']['files_photo_resize_error'] += 1
            request.app.logger.exception(
                'Get resize error', exc_info=f.exception())
            return
        name = cachename
    else:
        name = photo.name

    url = settings.MEDIA_URL + name
    return url, photo.mime_type


async def photo_handler(request, uuid, width, height, retina):
    request.app['state']['files_photo_request'] += 1
    try:
        UUID(uuid)
    except ValueError:
        raise web.HTTPNotFound()
    if width > 3000 or height > 2000:
        raise web.HTTPNotFound()
    if retina:
        width, height = 2 * width, 2 * height

    key = (uuid, width, height)
    f = cache.get(key)
    if not f:
        f = cache[key] = asyncio.ensure_future(
            get_resized_image(request, uuid, width, height))
    if not f.done():
        request.app['state']['files_photo_cache_wait'] += 1
        result = await f
    elif f.cancelled():
        del cache[key]
        request.app['state']['files_photo_cache_cancel'] += 1
        request.app.logger.error('Cancel %s', uuid)
        return
    elif f.exception():
        request.app.logger.exception(
            'Get resized photo error', exc_info=f.exception())
        return
    else:
        request.app['state']['files_photo_from_cache'] += 1
        result = f.result()

    if result:
        url, mimetype = result
        return aviews.response_file(url, mimetype)
    raise web.HTTPNotFound()
