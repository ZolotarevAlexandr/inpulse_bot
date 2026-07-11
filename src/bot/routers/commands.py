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
