from aiogram.types import Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import SwitchTo, Cancel, Column
from aiogram_dialog.widgets.text import Const, Format, Multi
from aiogram_dialog.widgets.input import TextInput

from src.bot.states import AdminSG
from src.db.database import db
from src.db.repositories.whitelist import WhitelistRepository


async def admin_getter(dialog_manager: DialogManager, **kwargs):
    async with db.session_factory() as session:
        repo = WhitelistRepository(session)
        whitelisted = await repo.list_whitelisted_users()
        
    whitelisted_str = "\n".join([f"- <code>{uid}</code>" for uid in whitelisted]) if whitelisted else "No users in whitelist."
    return {"whitelisted": whitelisted_str}


async def on_add_user(message: Message, widget, dialog_manager: DialogManager, text: str):
    try:
        telegram_id = int(text)
    except ValueError:
        await message.answer("Invalid Telegram ID. It should be a number.")
        return
        
    async with db.session_factory() as session:
        repo = WhitelistRepository(session)
        await repo.add_to_whitelist(telegram_id, added_by=message.from_user.id)
        await session.commit()
        
    await message.answer(f"✅ User <code>{telegram_id}</code> added to whitelist.")
    await dialog_manager.switch_to(AdminSG.menu)


async def on_remove_user(message: Message, widget, dialog_manager: DialogManager, text: str):
    try:
        telegram_id = int(text)
    except ValueError:
        await message.answer("Invalid Telegram ID. It should be a number.")
        return
        
    async with db.session_factory() as session:
        repo = WhitelistRepository(session)
        await repo.remove_from_whitelist(telegram_id)
        await session.commit()
        
    await message.answer(f"✅ User <code>{telegram_id}</code> removed from whitelist.")
    await dialog_manager.switch_to(AdminSG.menu)


dialog = Dialog(
    Window(
        Multi(
            Const("🛠 <b>Admin Panel</b>\n"),
            Const("<b>Whitelisted Users:</b>"),
            Format("{whitelisted}")
        ),
        Column(
            SwitchTo(Const("➕ Add User"), id="add_user", state=AdminSG.input_add),
            SwitchTo(Const("➖ Remove User"), id="remove_user", state=AdminSG.input_remove),
            Cancel(Const("⬅️ Close Admin Panel")),
        ),
        state=AdminSG.menu,
        getter=admin_getter,
    ),
    Window(
        Const("Please enter the Telegram ID of the user you want to add to the whitelist:"),
        TextInput(id="add_input", on_success=on_add_user),
        SwitchTo(Const("⬅️ Back"), id="back", state=AdminSG.menu),
        state=AdminSG.input_add,
    ),
    Window(
        Const("Please enter the Telegram ID of the user you want to remove from the whitelist:"),
        TextInput(id="remove_input", on_success=on_remove_user),
        SwitchTo(Const("⬅️ Back"), id="back", state=AdminSG.menu),
        state=AdminSG.input_remove,
    ),
)
