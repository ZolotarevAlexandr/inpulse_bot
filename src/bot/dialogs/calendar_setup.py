
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, ScrollingGroup, Select, SwitchTo
from aiogram_dialog.widgets.text import Const, Format

from src.bot.states import CalendarSetupSG
from src.db.database import db
from src.db.repositories.calendars import CalendarRepository
from src.db.repositories.users import UserRepository
from src.modules.calendar.service import CalendarService


async def get_internal_user_id(session, telegram_id: int) -> int | None:
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(telegram_id)
    return user["id"] if user else None


async def calendar_getter(dialog_manager: DialogManager, **kwargs):
    telegram_id = dialog_manager.event.from_user.id
    async with db.session_factory() as session:
        user_id = await get_internal_user_id(session, telegram_id)
        if not user_id:
            return {"has_calendars": False, "calendars": []}
            
        repo = CalendarRepository(session)
        calendars = await repo.get_calendars_for_user(user_id)
        
    for c in calendars:
        if c["last_synced"]:
            c["synced_str"] = c["last_synced"].strftime("%Y-%m-%d %H:%M")
        else:
            c["synced_str"] = "Never"
            
    return {
        "has_calendars": len(calendars) > 0,
        "calendars": calendars,
    }


async def on_calendar_selected(c: CallbackQuery, widget, dialog_manager: DialogManager, item_id: str):
    dialog_manager.dialog_data["selected_calendar_id"] = int(item_id)
    await dialog_manager.switch_to(CalendarSetupSG.detail)


async def calendar_detail_getter(dialog_manager: DialogManager, **kwargs):
    calendar_id = dialog_manager.dialog_data.get("selected_calendar_id")
    telegram_id = dialog_manager.event.from_user.id
    async with db.session_factory() as session:
        user_id = await get_internal_user_id(session, telegram_id)
        if not user_id:
            return {"name": "Not found", "type": "", "synced_str": ""}
            
        repo = CalendarRepository(session)
        calendars = await repo.get_calendars_for_user(user_id)
        
    cal = next((c for c in calendars if c["id"] == calendar_id), None)
    if not cal:
        return {"name": "Not found", "type": "", "synced_str": ""}
        
    synced_str = cal["last_synced"].strftime("%Y-%m-%d %H:%M") if cal["last_synced"] else "Never"
    
    return {
        "name": cal["name"],
        "type": cal["type"],
        "synced_str": synced_str
    }


async def on_delete_calendar(c: CallbackQuery, widget, dialog_manager: DialogManager):
    calendar_id = dialog_manager.dialog_data.get("selected_calendar_id")
    telegram_id = c.from_user.id
    async with db.session_factory() as session:
        user_id = await get_internal_user_id(session, telegram_id)
        if user_id:
            service = CalendarService(session)
            await service.delete_calendar(calendar_id, user_id)
            await session.commit()
        
    await c.answer("Calendar deleted!")
    await dialog_manager.switch_to(CalendarSetupSG.info)


async def on_sync_calendar(c: CallbackQuery, widget, dialog_manager: DialogManager):
    calendar_id = dialog_manager.dialog_data.get("selected_calendar_id")
    telegram_id = c.from_user.id
    
    async with db.session_factory() as session:
        user_id = await get_internal_user_id(session, telegram_id)
        if not user_id:
            await c.answer("User not found.")
            return
            
        repo = CalendarRepository(session)
        calendars = await repo.get_calendars_for_user(user_id)
        cal = next((c for c in calendars if c["id"] == calendar_id), None)
        
        if cal:
            service = CalendarService(session)
            await c.answer("Syncing calendar...")
            try:
                events_count = await service.sync_calendar(cal)
                await session.commit()
                await c.message.answer(f"✅ Sync complete! Inserted {events_count} events.")
            except Exception:
                await c.message.answer("❌ Sync failed. Make sure the file or URL is valid.")
                
    await dialog_manager.switch_to(CalendarSetupSG.info)


async def on_sync_all(c: CallbackQuery, widget, dialog_manager: DialogManager):
    telegram_id = c.from_user.id
    await c.answer("Syncing all calendars...")
    
    async with db.session_factory() as session:
        user_id = await get_internal_user_id(session, telegram_id)
        if user_id:
            service = CalendarService(session)
            events_count = await service.sync_all_for_user(user_id)
            await session.commit()
            await c.message.answer(f"✅ All calendars synced! Total events: {events_count}")
        else:
            await c.message.answer("❌ User not found.")


async def on_url_entered(message: Message, widget, dialog_manager: DialogManager, text: str):
    if not text.startswith("http"):
        await message.answer("Please enter a valid URL.")
        return

    telegram_id = message.from_user.id
    
    async with db.session_factory() as session:
        user_id = await get_internal_user_id(session, telegram_id)
        if not user_id:
            await message.answer("❌ User not found.")
            return
            
        service = CalendarService(session)
        try:
            await service.add_url_calendar(user_id, "URL Calendar", text)
            await session.commit()
            await message.answer("✅ URL Calendar added successfully!")
        except Exception:
            await message.answer("❌ Failed to parse calendar URL.")

    await dialog_manager.switch_to(CalendarSetupSG.info)


async def on_file_entered(message: Message, widget, dialog_manager: DialogManager):
    if not message.document or not message.document.file_name.endswith('.ics'):
        await message.answer("Please send a valid .ics file.")
        return

    telegram_id = message.from_user.id
    bot = message.bot
    
    file = await bot.get_file(message.document.file_id)
    file_bytes = await bot.download_file(file.file_path)
    file_content = file_bytes.read()
    
    async with db.session_factory() as session:
        user_id = await get_internal_user_id(session, telegram_id)
        if not user_id:
            await message.answer("❌ User not found.")
            return
            
        service = CalendarService(session)
        try:
            await service.add_file_calendar(user_id, message.document.file_name, file_content)
            await session.commit()
            await message.answer("✅ File Calendar added successfully!")
        except Exception:
            await message.answer("❌ Failed to parse calendar file. Check if it's a valid .ics format.")

    await dialog_manager.switch_to(CalendarSetupSG.info)


dialog = Dialog(
    Window(
        Const("📅 <b>Your Calendars</b>\n"),
        Format("You have connected calendars:", when="has_calendars"),
        Const("No calendars connected yet. Add one to get task recommendations based on your free time!", when=lambda data, widget, manager: not data.get("has_calendars")),
        ScrollingGroup(
            Select(
                Format("📅 {item[name]} ({item[type]}) - {item[synced_str]}"),
                id="cals",
                item_id_getter=lambda x: x["id"],
                items="calendars",
                on_click=on_calendar_selected,
            ),
            id="cals_sg",
            width=1,
            height=5,
            when="has_calendars"
        ),
        Column(
            SwitchTo(Const("➕ Add via URL"), id="add_url", state=CalendarSetupSG.input_url),
            SwitchTo(Const("➕ Add .ics File"), id="add_file", state=CalendarSetupSG.input_file),
            Button(Const("🔄 Sync All"), id="sync_all", on_click=on_sync_all, when="has_calendars"),
            Cancel(Const("⬅️ Back to Menu")),
        ),
        state=CalendarSetupSG.info,
        getter=calendar_getter,
    ),
    Window(
        Const("📅 <b>Calendar Details</b>\n"),
        Format("Name: {name}"),
        Format("Type: {type}"),
        Format("Last synced: {synced_str}"),
        Column(
            Button(Const("🔄 Sync Now"), id="sync_one", on_click=on_sync_calendar),
            Button(Const("🗑 Delete Calendar"), id="delete_cal", on_click=on_delete_calendar),
            SwitchTo(Const("⬅️ Back"), id="back", state=CalendarSetupSG.info),
        ),
        state=CalendarSetupSG.detail,
        getter=calendar_detail_getter,
    ),
    Window(
        Const("🔗 Please enter your iCal link (e.g. from Google Calendar settings):"),
        TextInput(id="ical_input", on_success=on_url_entered),
        SwitchTo(Const("⬅️ Cancel"), id="cancel", state=CalendarSetupSG.info),
        state=CalendarSetupSG.input_url,
    ),
    Window(
        Const("📁 Please upload your exported .ics file:"),
        MessageInput(on_file_entered),
        SwitchTo(Const("⬅️ Cancel"), id="cancel", state=CalendarSetupSG.info),
        state=CalendarSetupSG.input_file,
    ),
)
