from sqlalchemy import table, column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from ..amodels import Model


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
