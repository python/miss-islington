import os

os.environ.setdefault("REDIS_URL", "redis://localhost")

from aiohttp import web

from miss_islington import __main__ as main


# simple heallth check to amke sure /health works
async def test_health_check(aiohttp_client):
    app = web.Application()
    app.router.add_get("/health", main.health_check)
    client = await aiohttp_client(app)
    response = await client.get("/health")
    assert response.status == 200
    assert await response.text() == "OK"
