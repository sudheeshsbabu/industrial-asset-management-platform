import uuid

from aiohttp import web

@web.middleware
async def request_id_middleware(request, handler):
    request["request_id"] = str(uuid.uuid4())
    response = await handler(request)
    response.headers["X-Request-ID"] = request["request_id"]
    return response