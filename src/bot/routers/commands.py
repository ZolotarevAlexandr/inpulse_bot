import datetime
import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from src.bot.states import RootSG
from src.config import settings
from src.db.database import db
from src.db.repositories.users import UserRepository

logger = logging.getLogger(__name__)
router = Router()

_bot_started_at = datetime.datetime.now()


@router.message(CommandStart())
async def start_cmd(message: Message, dialog_manager: DialogManager):
    user = message.from_user
    if not user:
        return
        
    async with db.session_factory() as session:
        repo = UserRepository(session)
        existing_user = await repo.get_by_telegram_id(user.id)
        if not existing_user:
            await repo.create_user(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name
            )
            await session.commit()
            logger.info(f"[ANALYTICS] User {user.id} (@{user.username}) signed up")
            
    logger.info(f"[ANALYTICS] User {user.id} (@{user.username}) started session")
    await dialog_manager.start(RootSG.main, mode=StartMode.RESET_STACK)


@router.message(Command("menu"))
async def menu_cmd(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(RootSG.main, mode=StartMode.RESET_STACK)


@router.message(Command("help"))
async def help_cmd(message: Message):
    text = (
        "InPulse Bot MVP\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/menu - Open main menu\n"
        "/help - Show this message\n"
    )
    if message.from_user and message.from_user.id in settings.telegram_bot.admins:
        text += "/admin - Open admin panel\n"
        text += "/statistics - Show bot statistics\n"
    await message.answer(text)


@router.message(Command("admin"))
async def admin_cmd(message: Message, dialog_manager: DialogManager):
    user = message.from_user
    if user and user.id in settings.telegram_bot.admins:
        from src.bot.states import AdminSG
        await dialog_manager.start(AdminSG.menu, mode=StartMode.RESET_STACK)
    else:
        await message.answer("⛔ Access denied.")


@router.message(Command("inform"))
async def inform_cmd(message: Message, dialog_manager: DialogManager):
    user = message.from_user
    if user and user.id in settings.telegram_bot.admins:
        from src.bot.states import AdminSG
        await dialog_manager.start(AdminSG.inform_upload, mode=StartMode.RESET_STACK)
    else:
        await message.answer("⛔ Access denied.")


def _format_uptime(delta: datetime.timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def _pct(value: float | None) -> str:
    return f"{value}%" if value is not None else "—"


@router.message(Command("statistics"))
async def statistics_cmd(message: Message):
    user = message.from_user
    if not user or user.id not in settings.telegram_bot.admins:
        await message.answer("⛔ Access denied.")
        return

    from src.db.repositories.statistics import StatisticsRepository

    async with db.session_factory() as session:
        repo = StatisticsRepository(session)
        s = await repo.collect()

    uptime = _format_uptime(datetime.datetime.now() - _bot_started_at)
    llm_status = "✅ Configured" if settings.llm else "❌ Not configured"

    text = (
        "📊 <b>Bot Statistics</b>\n"
        "\n"
        "👥 <b>Users</b>\n"
        f"  Total: <b>{s.total_users}</b>\n"
        f"  New today: {s.new_users_today}\n"
        f"  New (7d): {s.new_users_7d}  ·  (30d): {s.new_users_30d}\n"
        f"  Premium: {s.premium_users}  ·  Free: {s.free_users}\n"
        "\n"
        "✅ <b>Tasks</b>\n"
        f"  Total: <b>{s.total_tasks}</b>\n"
        f"  Active: {s.active_tasks}  ·  Done: {s.completed_tasks}\n"
        f"  Done today: {s.completed_today}  ·  (7d): {s.completed_7d}\n"
        f"  Avg per user: {s.avg_tasks_per_user}\n"
        "\n"
        "📅 <b>Calendars</b>\n"
        f"  Total: <b>{s.total_calendars}</b> (URL: {s.url_calendars} · File: {s.file_calendars})\n"
        f"  Events synced: {s.total_events}\n"
        f"  Users with calendars: {s.users_with_calendars}\n"
        "\n"
        "🤖 <b>Recommendations</b>\n"
        f"  Total shown: <b>{s.total_recommendations}</b>\n"
        f"  Shown today: {s.recommendations_today}\n"
        f"  Acceptance rate: {_pct(s.acceptance_rate)}\n"
        f"  Completion rate: {_pct(s.completion_rate)}\n"
        "\n"
        "⚙️ <b>System</b>\n"
        f"  Uptime: {uptime}\n"
        f"  Environment: {settings.environment.value}\n"
        f"  LLM: {llm_status}\n"
    )

    await message.answer(text)

