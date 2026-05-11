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
        f"[Request ID: {request['request_id']}] "
        f"Request: {request.method} "
        f"{request.path} "
        f"Status: {response.status} "
        f"Duration: {duration:.4f}s"
    )
    return response

    