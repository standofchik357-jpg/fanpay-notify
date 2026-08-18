import asyncio
import os
import threading

from aiohttp import web

from app.bot import start_bot


async def health(request):
    return web.Response(text="Bot is running")


def start_web():
    app = web.Application()
    app.router.add_get("/", health)

    web.run_app(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 10000))
    )


async def main():

    threading.Thread(
        target=start_web,
        daemon=True
    ).start()

    await start_bot()


if __name__ == "__main__":

    asyncio.run(main())