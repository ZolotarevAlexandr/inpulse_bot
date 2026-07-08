import datetime

from aiogram.types import Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import SwitchTo, Cancel, Column, Button, Start
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.input import TextInput

from src.bot.states import AdminSG, RootSG
from src.db.database import db
from src.db.repositories.users import UserRepository


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
        
    role_str = "Premium ⭐" if is_premium else "Free"
    premium_until = user.get("premium_until")
    premium_until_str = premium_until.strftime("%d.%m.%Y") if premium_until else "N/A"
    
    return {
        "tg_id": user["telegram_id"],
        "username": user["username"] or "No username",
        "role_str": role_str,
        "premium_until": premium_until_str,
        "is_premium": is_premium,
    }


async def on_grant_duration(message: Message, widget, dialog_manager: DialogManager, text: str):
    try:
        days = int(text)
        if days <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Please enter a valid number of days (> 0).")
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
        
    await message.answer(f"✅ User Premium {action_text} until {until.strftime('%d.%m.%Y')}.")
    
    from aiogram import Bot
    bot: Bot = dialog_manager.middleware_data["bot"]
    try:
        await bot.send_message(
            telegram_id, 
            f"🎉 Your Premium subscription has been {action_text} until {until.strftime('%d.%m.%Y')}! Enjoy unlimited recommendations."
        )
    except Exception:
        await message.answer("⚠️ Could not send notification to user (they might have blocked the bot).")
        
    await dialog_manager.switch_to(AdminSG.user_detail)


async def revoke_premium(call: Message, button: Button, dialog_manager: DialogManager):
    user_id = dialog_manager.dialog_data["target_user_id"]
    async with db.session_factory() as session:
        repo = UserRepository(session)
        await repo.remove_premium(user_id)
        await session.commit()
        
    await call.answer("Premium revoked.", show_alert=True)
    await dialog_manager.switch_to(AdminSG.user_detail)


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
            Format("<b>Premium until:</b> {premium_until}\n"),
        ),
        Column(
            SwitchTo(Const("⭐ Grant Premium"), id="grant_prem", state=AdminSG.select_duration, when=lambda data, w, m: not data.get("is_premium")),
            SwitchTo(Const("⭐ Extend Premium"), id="extend_prem", state=AdminSG.select_duration, when="is_premium"),
            Button(Const("❌ Revoke Premium"), id="revoke_prem", on_click=revoke_premium, when="is_premium"),
            SwitchTo(Const("⬅️ Back to Menu"), id="back", state=AdminSG.menu),
        ),
        state=AdminSG.user_detail,
        getter=user_detail_getter,
    ),
    Window(
        Const("Enter the number of days to grant Premium for (e.g. 30):"),
        TextInput(id="duration_input", on_success=on_grant_duration),
        SwitchTo(Const("⬅️ Back"), id="back", state=AdminSG.user_detail),
        state=AdminSG.select_duration,
    )
)
