import datetime
import json

from aiogram.types import Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Column, Start, SwitchTo
from aiogram_dialog.widgets.text import Const, Format, Multi

from src.bot.states import AdminSG, RootSG
from src.db.database import db
from src.db.repositories.users import UserRepository

BOT_LAUNCH_MESSAGE = """
Hi! That's InPulse again and we're glad to announce that bot is up and running now!

inPulse turns every free window between classes into a completed task.
You're free for 20-60 minutes and you don't know what to do? The bot will suggest one suitable task, taking into account the schedule, deadlines and priorities.

Just type /start, connect your calendar and add some tasks
"""


async def admin_getter(dialog_manager: DialogManager, **kwargs):
    async with db.session_factory() as session:
        repo = UserRepository(session)
        users = await repo.get_all_users()
        
    users_str = "\n".join([f"- <code>{u['telegram_id']}</code> (@{u['username'] or 'no_user'}) [{u['role']}]" for u in users[:20]])
    if len(users) > 20:
        users_str += f"\n... and {len(users) - 20} more."
        
    return {"users_str": users_str}


async def on_find_user(message: Message, widget, dialog_manager: DialogManager, text: str):
    user = None
    async with db.session_factory() as session:
        repo = UserRepository(session)
        
        if text.isdigit():
            user = await repo.get_by_telegram_id(int(text))
            
        if not user:
            username = text.lstrip("@")
            user = await repo.get_by_username(username)
            
    if not user:
        await message.answer(f"User '{text}' not found in database.")
        return
        
    dialog_manager.dialog_data["target_user_id"] = user["id"]
    dialog_manager.dialog_data["target_telegram_id"] = user["telegram_id"]
    await dialog_manager.switch_to(AdminSG.user_detail)


async def user_detail_getter(dialog_manager: DialogManager, **kwargs):
    user_id = dialog_manager.dialog_data.get("target_user_id")
    async with db.session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)
        is_premium = await repo.is_premium(user_id)
        
    role_str = "InPulse Pro ⭐" if is_premium else "Free"
    premium_until = user.get("premium_until")
    premium_until_str = premium_until.strftime("%d.%m.%Y") if premium_until else "N/A"
    
    return {
        "tg_id": user["telegram_id"],
        "username": user["username"] or "No username",
        "role_str": role_str,
        "premium_until": premium_until_str,
        "is_premium": is_premium,
    }


import logging

logger = logging.getLogger(__name__)

async def on_grant_duration(message: Message, widget, dialog_manager: DialogManager, text: str):
    try:
        days = int(text)
        if days <= 0 or days > 36500:
            raise ValueError
    except ValueError:
        await message.answer("Please enter a valid number of days (1 to 36500).")
        return
        
    user_id = dialog_manager.dialog_data["target_user_id"]
    telegram_id = dialog_manager.dialog_data["target_telegram_id"]
    
    async with db.session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)
        
        current_premium_until = user.get("premium_until")
        if current_premium_until and current_premium_until > datetime.datetime.now():
            until = current_premium_until + datetime.timedelta(days=days)
            action_text = "extended"
        else:
            until = datetime.datetime.now() + datetime.timedelta(days=days)
            action_text = "activated"
            
        await repo.set_premium(user_id, until)
        await session.commit()
        
        logger.info(f"Admin {message.from_user.id} granted/extended InPulse Pro for User {user_id} (@{user['username']}) until {until}")
        logger.info(f"[ANALYTICS] Admin granted InPulse Pro for User {user_id} (@{user['username']})")
        
    await message.answer(f"✅ User InPulse Pro {action_text} until {until.strftime('%d.%m.%Y')}.")
    
    from aiogram import Bot
    bot: Bot = dialog_manager.middleware_data["bot"]
    try:
        await bot.send_message(
            telegram_id, 
            f"🎉 Your InPulse Pro subscription has been {action_text} until {until.strftime('%d.%m.%Y')}! Enjoy unlimited recommendations."
        )
    except Exception:
        await message.answer("⚠️ Could not send notification to user (they might have blocked the bot).")
        
    await dialog_manager.switch_to(AdminSG.user_detail)


async def revoke_premium(call: Message, button: Button, dialog_manager: DialogManager):
    user_id = dialog_manager.dialog_data["target_user_id"]
    async with db.session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_id(user_id)
        await repo.remove_premium(user_id)
        await session.commit()
        
        logger.info(f"Admin {call.from_user.id} revoked InPulse Pro for User {user_id} (@{user['username']})")
        logger.info(f"[ANALYTICS] Admin revoked InPulse Pro for User {user_id} (@{user['username']})")
        
    await call.answer("InPulse Pro revoked.", show_alert=True)
    await dialog_manager.switch_to(AdminSG.user_detail)


async def on_inform_file_entered(message: Message, widget, dialog_manager: DialogManager):
    if not message.document or not message.document.file_name.endswith('.json'):
        await message.answer("Please send a valid .json file.")
        return

    bot = message.bot
    file = await bot.get_file(message.document.file_id)
    file_bytes = await bot.download_file(file.file_path)
    
    try:
        data = json.loads(file_bytes.read().decode('utf-8'))
        users = data.get("users", [])
        if not isinstance(users, list):
            raise ValueError
    except Exception:
        await message.answer('Invalid JSON format. Expected format: {"users": [123, 456]}')
        return

    success_count = 0
    for uid in users:
        try:
            await bot.send_message(uid, BOT_LAUNCH_MESSAGE)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {uid}: {e}")

    await message.answer(f"✅ Notification sent to {success_count}/{len(users)} users.")
    await dialog_manager.switch_to(AdminSG.menu)


dialog = Dialog(
    Window(
        Multi(
            Const("🛠 <b>Admin Panel</b>\n"),
            Const("<b>Recent Users:</b>"),
            Format("{users_str}")
        ),
        Column(
            SwitchTo(Const("🔍 Find User"), id="find_user", state=AdminSG.input_find),
            Start(Const("⬅️ Close Admin Panel"), id="close_admin", state=RootSG.main),
        ),
        state=AdminSG.menu,
        getter=admin_getter,
    ),
    Window(
        Const("Please enter the Telegram ID or username of the user you want to find:"),
        TextInput(id="find_input", on_success=on_find_user),
        SwitchTo(Const("⬅️ Back"), id="back", state=AdminSG.menu),
        state=AdminSG.input_find,
    ),
    Window(
        Multi(
            Const("👤 <b>User Details</b>\n"),
            Format("<b>ID:</b> <code>{tg_id}</code>"),
            Format("<b>Username:</b> @{username}"),
            Format("<b>Status:</b> {role_str}"),
            Format("<b>InPulse Pro until:</b> {premium_until}\n"),
        ),
        Column(
            SwitchTo(Const("⭐ Grant InPulse Pro"), id="grant_prem", state=AdminSG.select_duration, when=lambda data, w, m: not data.get("is_premium")),
            SwitchTo(Const("⭐ Extend InPulse Pro"), id="extend_prem", state=AdminSG.select_duration, when="is_premium"),
            Button(Const("❌ Revoke InPulse Pro"), id="revoke_prem", on_click=revoke_premium, when="is_premium"),
            SwitchTo(Const("⬅️ Back to Menu"), id="back", state=AdminSG.menu),
        ),
        state=AdminSG.user_detail,
        getter=user_detail_getter,
    ),
    Window(
        Const("Enter the number of days to grant InPulse Pro for (e.g. 30):"),
        TextInput(id="duration_input", on_success=on_grant_duration),
        SwitchTo(Const("⬅️ Back"), id="back", state=AdminSG.user_detail),
        state=AdminSG.select_duration,
    ),
    Window(
        Const("📁 Please upload a JSON file with user IDs to inform them that the bot is up:"),
        MessageInput(on_inform_file_entered),
        SwitchTo(Const("⬅️ Cancel"), id="cancel", state=AdminSG.menu),
        state=AdminSG.inform_upload,
    )
)
