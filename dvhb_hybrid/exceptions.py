"""
DEPRECATED module. Use aiohttp.web_exceptions instead
"""

import json

import aiohttp.web
from aiohttp.web import HTTPException

from .aviews import JsonEncoder


DEFAULT_CONTENT_TYPE = 'application/json;charset=utf-8'


class JsonHTTPException:
    content_type = DEFAULT_CONTENT_TYPE

    def as_dict(self):
        return {
            'status': self.status,
            'errors': {
                '__all__': [
                    self.reason
                ]
            }}

    @property
    def body(self):
        if self._body:
            return self._body
        self._body = json.dumps(
            self.as_dict(),
            cls=JsonEncoder,
            ensure_ascii=False,
            indent=3).encode()
        return self._body

    @body.setter
    def body(self, body):
        self._body = body


class JsonHTTPMessage(JsonHTTPException):

    def __init__(self, *, headers=None, reason=None,
                 body=None, text=None, content_type=None, **kwargs):
        self._data = kwargs
        HTTPException.__init__(
            self, reason=reason, headers=headers, body=body,
            text=text, content_type=content_type)

    def as_dict(self):
        return {
            **self._data,
            'status': self.status,
            'message': self.reason,
        }


class HTTPOk(JsonHTTPMessage, aiohttp.web.HTTPOk):
    # Workaround for bug in aiohttp (see https://github.com/aio-libs/aiohttp/issues/1718). Seems to be fixed in 2.3.1
    _body_payload = False
    pass


class HTTPCreated(JsonHTTPMessage, aiohttp.web.HTTPCreated):
    pass


class HTTPAccepted(JsonHTTPMessage, aiohttp.web.HTTPAccepted):
    pass


class HTTPNoContent(JsonHTTPMessage, aiohttp.web.HTTPNoContent):
    pass


class HTTPResetContent(JsonHTTPMessage, aiohttp.web.HTTPResetContent):
    pass


class HTTPPartialContent(JsonHTTPMessage, aiohttp.web.HTTPPartialContent):
    pass


class HTTPBadRequest(JsonHTTPException, aiohttp.web.HTTPBadRequest):

    def __init__(self, *, headers=None, reason=None, errors=None,
                 body=None, text=None, content_type=None):
        self._errors = errors
        super(HTTPBadRequest, self).__init__(
            reason=reason, headers=headers, body=body,
            text=text, content_type=content_type)

    def as_dict(self):
        result = super(HTTPBadRequest, self).as_dict()
        if self._errors:
            result['errors'].update(self._errors)
        return result


class HTTPUnauthorized(JsonHTTPException, aiohttp.web.HTTPUnauthorized):
    pass


class HTTPForbidden(JsonHTTPException, aiohttp.web.HTTPForbidden):
    pass


class HTTPNotFound(JsonHTTPException, aiohttp.web.HTTPNotFound):
    pass


class NotFound(HTTPNotFound):
    pass


class HTTPGone(JsonHTTPException, aiohttp.web.HTTPGone):
    pass


class HTTPConflict(JsonHTTPException, aiohttp.web.HTTPConflict):
    pass


class HTTPRequestRangeNotSatisfiable(
        JsonHTTPException, aiohttp.web.HTTPRequestRangeNotSatisfiable):
    pass


class HTTPRequestEntityTooLarge(
        JsonHTTPException, aiohttp.web.HTTPRequestEntityTooLarge):
    pass


class HTTPNotAcceptable(
        JsonHTTPException, aiohttp.web.HTTPNotAcceptable):
    pass


class HTTPLocked(
        JsonHTTPException, aiohttp.web.HTTPClientError):
    status_code = 423


class HTTPServiceUnavailable(
        JsonHTTPException, aiohttp.web.HTTPServiceUnavailable):
    pass
