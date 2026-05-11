import logging
import traceback

from aiohttp import web
from pydantic import ValidationError

from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

@web.middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)
    except ValidationError as e:
        return web.json_response({
            "success": False,
            "error": {
                "type": "validation_error",
                "details": e.errors()
            },
        }, status=400)
    except AppError as e:
        return web.json_response({
            "success": False,
            "error": {
                "type": e.__class__.__name__,
                "message": e.message
            }
        }, status=e.status_code)
    except Exception as e:
        logger.error("Unhandler server error")
        return web.json_response({
            "success": False,
            "error": {
                "type": "internal_server_error",
                "message": "Internal Server Error"
            }
        }, status=500)