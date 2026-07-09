import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
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
    admin_dialog,
    calendar_setup_dialog,
    recommend_dialog,
    root_dialog,
    task_create_dialog,
    task_list_dialog,
    account_dialog,
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

async def main():
    if settings.llm:
        logger.info("LLM configured. Recommendations will use it when requests succeed.")
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
