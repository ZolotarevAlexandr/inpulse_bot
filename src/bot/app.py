import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram_dialog import setup_dialogs

from src.bot.middlewares.whitelist import WhitelistMiddleware
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

dp = Dispatcher(storage=storage)

whitelist_middleware = WhitelistMiddleware()
dp.message.middleware(whitelist_middleware)
dp.callback_query.middleware(whitelist_middleware)

from src.bot.dialogs import (
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

setup_dialogs(dp)

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.bot.jobs import sync_all_url_calendars

from openai import AsyncOpenAI

async def main():
    if settings.llm:
        logger.info("Checking LLM connection to %s...", settings.llm.base_url)
        try:
            client = AsyncOpenAI(
                api_key=settings.llm.api_key.get_secret_value(),
                base_url=settings.llm.base_url
            )
            await client.models.list(timeout=5.0)
            logger.info("LLM connection successful. Using LLM for recommendations.")
        except Exception as e:
            logger.warning("LLM connection failed: %s. Falling back to static recommendations.", e)
            settings.llm = None
    else:
        logger.info("No LLM configured. Using static recommendations.")

    logger.info("Starting scheduler...")
    scheduler = AsyncIOScheduler()
    # Run sync every hour
    scheduler.add_job(
        sync_all_url_calendars, 
        'interval', 
        minutes=settings.ical_refresh_interval_minutes or 60
    )
    scheduler.start()

    logger.info("Bot starting...")
    # Drop pending updates
    await bot.delete_webhook(drop_pending_updates=True)
    # Start long-polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await dp.storage.close()
        await bot.session.close()
