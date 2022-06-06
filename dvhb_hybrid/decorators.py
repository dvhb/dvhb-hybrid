import functools

from aiohttp import ClientSession
from aiohttp.web import HTTPNotAcceptable, HTTPOk


RECAPTCHA_FIELD = 'g-recaptcha-response'


def recaptcha(arg):
    """
    Decorator to verify recaptcha response.

    Required properties in "recaptcha" config section:
        url - url to send request.
        active - true if recaptcha verification is active.
        secret - code to access api.
    """
    def with_arg(view):
        @functools.wraps(view)
        async def wrapper(**kwargs):
            request = kwargs['request']
            c = request.app.config.recaptcha
            response = None
            if RECAPTCHA_FIELD in request:
                response = request[RECAPTCHA_FIELD]
            else:
                for v in kwargs.values():
                    if isinstance(v, dict) and RECAPTCHA_FIELD in v:
                        response = v.pop(RECAPTCHA_FIELD)
                        break

            if not c.active:
                return await view(**kwargs)

            if response:
                async with ClientSession() as client:
                    async with client.post(c.url, data={'secret': c.secret, 'response': response}) as r:
                        if r.status == HTTPOk.status_code:
                            data = await r.json()
                            if data['success']:
                                return await view(**kwargs)

            raise HTTPNotAcceptable(reason='Wrong recaptcha')

        return wrapper

    if not callable(arg):
        return with_arg
    return with_arg(arg)
