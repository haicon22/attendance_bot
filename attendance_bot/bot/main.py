# attendance_bot/bot/main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from config.settings import get_settings
from core.database import init_db, close_db
from core.redis_client import get_redis
from bot.handlers import (
    start_router,
    attendance_router,
    leave_router,
    profile_router,
    admin_router,
)
from bot.middlewares import (
    AuthMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
)

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    logger.info("Bot starting up...")
    await init_db()

    if settings.WEBHOOK_URL:
        await bot.set_webhook(
            url=f"{settings.WEBHOOK_URL}{settings.WEBHOOK_PATH}",
            secret_token=settings.WEBHOOK_SECRET,
        )
        logger.info(f"Webhook set to {settings.WEBHOOK_URL}{settings.WEBHOOK_PATH}")
    else:
        logger.info("Running in polling mode")


async def on_shutdown(bot: Bot):
    logger.info("Bot shutting down...")
    await close_db()
    if settings.WEBHOOK_URL:
        await bot.delete_webhook()


def create_dispatcher() -> Dispatcher:
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)

    # Register middlewares
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(RateLimitMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Register routers
    dp.include_router(start_router)
    dp.include_router(attendance_router)
    dp.include_router(leave_router)
    dp.include_router(profile_router)
    dp.include_router(admin_router)

    return dp


async def main():
    bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = create_dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    if settings.WEBHOOK_URL:
        app = web.Application()
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=settings.WEBHOOK_SECRET,
        )
        webhook_handler.register(app, path=settings.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=8080)
        await site.start()
        logger.info("Webhook server started on port 8080")
        await asyncio.Event().wait()
    else:
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
