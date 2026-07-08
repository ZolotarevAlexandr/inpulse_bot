import datetime

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Row, SwitchTo
from aiogram_dialog.widgets.text import Const

from src.bot.states import TaskCreateSG
from src.db.database import db
from src.db.repositories.users import UserRepository
from src.modules.tasks.service import TaskService


async def on_title_input(message: Message, widget, dialog_manager: DialogManager, text: str):
    dialog_manager.dialog_data["title"] = text
    await dialog_manager.switch_to(TaskCreateSG.input_deadline)


async def on_deadline_input(message: Message, widget, dialog_manager: DialogManager, text: str):
    # simple parsing DD.MM or DD.MM.YYYY
    try:
        if len(text) == 5:
            d = datetime.datetime.strptime(text, "%d.%m")
            d = d.replace(year=datetime.datetime.now().year)
        else:
            d = datetime.datetime.strptime(text, "%d.%m.%Y")
        dialog_manager.dialog_data["deadline"] = d.isoformat()
    except ValueError:
        await message.answer("Invalid date format. Use DD.MM or DD.MM.YYYY.")
        return
        
    await dialog_manager.switch_to(TaskCreateSG.input_priority)


async def skip_deadline(call: CallbackQuery, button: Button, dialog_manager: DialogManager):
    dialog_manager.dialog_data["deadline"] = None
    await dialog_manager.switch_to(TaskCreateSG.input_priority)


async def on_priority_click(call: CallbackQuery, button: Button, dialog_manager: DialogManager):
    priority = int(button.widget_id.split("_")[1])
    dialog_manager.dialog_data["priority"] = priority
    await dialog_manager.switch_to(TaskCreateSG.input_duration)


async def on_duration_input(message: Message, widget, dialog_manager: DialogManager, text: str):
    try:
        duration = int(text)
        if duration <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("Please send a valid number of minutes (> 0).")
        return
        
    # Create the task
    user_id = message.from_user.id
    async with db.session_factory() as session:
        repo = UserRepository(session)
        user = await repo.get_by_telegram_id(user_id)
        if user:
            task_service = TaskService(session)
            
            deadline_str = dialog_manager.dialog_data.get("deadline")
            deadline = datetime.datetime.fromisoformat(deadline_str) if deadline_str else None
            
            await task_service.create_task(
                user_id=user["id"],
                title=dialog_manager.dialog_data["title"],
                priority=dialog_manager.dialog_data["priority"],
                estimated_minutes=duration,
                deadline=deadline
            )
            await session.commit()
            
    await message.answer("✅ Task created successfully!")
    await dialog_manager.done()


dialog = Dialog(
    Window(
        Const("📝 <b>New Task</b>\n\nEnter the title of the task:"),
        TextInput(id="title_input", on_success=on_title_input),
        Cancel(Const("⬅️ Cancel")),
        state=TaskCreateSG.input_title,
    ),
    Window(
        Const("📅 Enter the deadline (DD.MM or DD.MM.YYYY) or skip:"),
        TextInput(id="deadline_input", on_success=on_deadline_input),
        Button(Const("⏭️ Skip"), id="skip_dl", on_click=skip_deadline),
        SwitchTo(Const("⬅️ Back"), id="back", state=TaskCreateSG.input_title),
        state=TaskCreateSG.input_deadline,
    ),
    Window(
        Const("⭐ Select the priority (1 = Low, 5 = High):"),
        Row(
            Button(Const("1"), id="p_1", on_click=on_priority_click),
            Button(Const("2"), id="p_2", on_click=on_priority_click),
            Button(Const("3"), id="p_3", on_click=on_priority_click),
            Button(Const("4"), id="p_4", on_click=on_priority_click),
            Button(Const("5"), id="p_5", on_click=on_priority_click),
        ),
        SwitchTo(Const("⬅️ Back"), id="back", state=TaskCreateSG.input_deadline),
        state=TaskCreateSG.input_priority,
    ),
    Window(
        Const("⏱ Enter the estimated duration in minutes (e.g., 30):"),
        TextInput(id="duration_input", on_success=on_duration_input),
        SwitchTo(Const("⬅️ Back"), id="back", state=TaskCreateSG.input_priority),
        state=TaskCreateSG.input_duration,
    ),
)
