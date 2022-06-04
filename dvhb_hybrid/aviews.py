import datetime
import functools
import json
import uuid
from typing import Any, Dict, Optional

from aiohttp import web
from aiohttp_apiset.views import ApiSet

from .redis import RedisMixin


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


class BaseView(RedisMixin, ApiSet):
    limit_body: Optional[int] = None

    @property
    def app(self):
        return self.request.app

    def check_size_body(self, request: web.Request, limit: Optional[int] = None):
        limit = limit or self.limit_body
        if not limit:
            return
        elif not request.content_length:
            raise self.response(status=411)
        elif request.content_length > limit:
            raise self.response(status=413)

    def list_params(self, data: Dict[str, Any], limit: int = 10, offset: int = 0):
        raw_limit = data.get('limit')
        if raw_limit is not None:
            try:
                limit = int(raw_limit)
                if not 1 <= limit < 1000:
                    raise ValueError()
            except (ValueError, TypeError):
                pass
        raw_offset = data.get('offset')
        if raw_offset is not None:
            try:
                offset = int(raw_offset)
                if offset is not None and not 0 <= offset:
                    raise ValueError()
            except (ValueError, TypeError):
                pass
        return limit, offset


def response_file(url, mime_type, filename=None):
    headers = {'X-Accel-Redirect': url}
    if filename:
        v = 'attachment; filename="{}"'.format(filename)
        headers['Content-Disposition'] = v
    raise web.HTTPOk(
        content_type=mime_type,
        headers=headers,
    )


async def http200(request):
    raise web.HTTPOk(body=b'')
