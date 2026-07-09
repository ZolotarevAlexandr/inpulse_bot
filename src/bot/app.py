import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from aiogram_dialog import setup_dialogs

from src.config import settings

logger = logging.getLogger(__name__)

bot = Bot(
    token=settings.telegram_bot.token.get_secret_value(),
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

if settings.redis_url:
    storage = RedisStorage.from_url(
        settings.redis_url.get_secret_value(),
        key_builder=DefaultKeyBuilder(with_destiny=True)
    )
    logger.info("Using Redis storage")
else:
    storage = MemoryStorage()
    logger.info("Using Memory storage")

from src.bot.middlewares import AuthMiddleware

dp = Dispatcher(storage=storage)

auth_middleware = AuthMiddleware()
dp.message.middleware(auth_middleware)
dp.callback_query.middleware(auth_middleware)

from src.bot.dialogs import (
    account_dialog,
    admin_dialog,
    calendar_setup_dialog,
    recommend_dialog,
    root_dialog,
    task_create_dialog,
    task_list_dialog,
)
from src.bot.routers.commands import router as commands_router

dp.include_router(commands_router)

dp.include_router(root_dialog)
dp.include_router(calendar_setup_dialog)
dp.include_router(task_create_dialog)
dp.include_router(task_list_dialog)
dp.include_router(recommend_dialog)
dp.include_router(admin_dialog)
dp.include_router(account_dialog)

setup_dialogs(dp)

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.bot.jobs import sync_all_url_calendars


def setup_scheduler() -> AsyncIOScheduler:
    logger.info("Starting scheduler...")
    scheduler = AsyncIOScheduler()
    # Run sync every hour
    scheduler.add_job(
        sync_all_url_calendars, 
        'interval', 
        minutes=settings.ical_refresh_interval_minutes or 60
    )
    scheduler.start()
    return scheduler

async def start_healthcheck_server():
    from aiohttp import web
    async def health_handler(request):
        return web.Response(text="OK")
        
    health_app = web.Application()
    health_app.router.add_get('/health', health_handler)
    runner = web.AppRunner(health_app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8080)
    await site.start()
    logger.info("Health check server listening on 127.0.0.1:8080")
    return runner

async def main():
    if settings.llm:
        logger.info("LLM configured. Recommendations will use it when requests succeed.")
    else:
        logger.info("No LLM configured. Using static recommendations.")

    scheduler = setup_scheduler()
    health_runner = await start_healthcheck_server()

    logger.info("Bot starting...")
    # Drop pending updates
    await bot.delete_webhook(drop_pending_updates=True)

    # Start long-polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await health_runner.cleanup()
        scheduler.shutdown()
        await dp.storage.close()
        await bot.session.close()
