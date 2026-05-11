import time
import logging

from aiohttp import web

logger = logging.getLogger(__name__)

@web.middleware
async def request_logging_middleware(request, handler):
    start = time.time()
    response = await handler(request)
    duration = time.time() - start

    logger.info(
        f"{request.method} {request.path} {response.status} {duration:.4f}s"
    )
    return response

    