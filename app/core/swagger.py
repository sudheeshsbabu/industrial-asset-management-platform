from aiohttp_apispec import setup_aiohttp_apispec


def setup_swagger(app):
    setup_aiohttp_apispec(
        app=app,

        title="AssetOps API",

        version="v1",

        url="/api/docs/swagger.json",

        swagger_path="/api/docs"
    )