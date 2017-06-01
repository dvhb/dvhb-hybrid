import mimetypes
from io import BytesIO

from aiohttp import client
from sqlalchemy import table, column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from ..amodels import Model
from .. import utils
from .storages import image_storage


class Image(Model):
    primary_key = 'uuid'
    table = table(
        'files_image',
        column('uuid', UUID(as_uuid=True)),
        column('image'),
        column('author_id'),
        column('created_at'),
        column('updated_at'),
        column('mime_type'),
        column('meta', JSONB),
    )

    @classmethod
    def set_defaults(cls, data: dict):
        data.setdefault('meta', {})
        data['updated_at'] = utils.now()

    @classmethod
    async def from_url(cls, url, *, user, connection=None):
        async with client.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return
                l = response.content_length
                if not l or l > 2 ** 23:
                    return
                content_type = response.content_type
                if not content_type.startswith('image'):
                    return
                content = BytesIO(await response.read())
                filename = response.url.name
        exts = mimetypes.guess_all_extensions(content_type)
        for ext in exts:
            if filename.endswith(ext):
                break
        else:
            if exts:
                filename += exts[-1]
        name = await cls.app.loop.run_in_executor(
            None, image_storage.save, filename, content)
        image_uuid = image_storage.uuid(name)
        return await cls.create(
            uuid=image_uuid,
            image=name,
            mime_type=content_type,
            created_at=utils.now(),
            author_id=user.pk,
            connection=connection
        )
