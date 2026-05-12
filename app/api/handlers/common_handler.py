from aiohttp import web

async def health(request):
    return web.json_response({"status" : "ok"})