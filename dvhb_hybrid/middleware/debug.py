import logging

from aiohttp.web_exceptions import HTTPException

logger = logging.getLogger()


async def debug_factory(app, handler):
    async def debug_middleware(request):
        try:
            response = await handler(request)
        except HTTPException:
            raise
        except:
            logger.exception('ERROR')
            raise
        return response
    return debug_middleware
