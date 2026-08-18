import asyncio
import os

from aiohttp import web

from app.bot import start_bot


async def health(request):
    return web.Response(text="Bot is running")


async def start_web():
    app = web.Application()
    app.router.add_get("/", health)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 10000))
    )

    await site.start()


async def main():
    await start_web()
    await start_bot()


if __name__ == "__main__":
    asyncio.run(main())