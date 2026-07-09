from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Column, Start
from aiogram_dialog.widgets.text import Const, Format

from src.bot.states import AccountSG, CalendarSetupSG, RecommendSG, RootSG, TaskListSG


async def on_startup(dialog_manager: DialogManager, **kwargs):
    user = dialog_manager.event.from_user
    return {"name": user.first_name}


dialog = Dialog(
    Window(
        Format("Hello, {name}!\n\nWelcome to InPulse. I can help you find a task to do in your free windows between classes."),
        Column(
            Start(Const("🎯 What to do now?"), id="btn_recommend", state=RecommendSG.show),
            Start(Const("📝 My Tasks"), id="btn_tasks", state=TaskListSG.list),
            Start(Const("📅 Calendar Setup"), id="btn_calendar", state=CalendarSetupSG.info),
            Start(Const("👤 Account"), id="btn_account", state=AccountSG.info),
        ),
        state=RootSG.main,
        getter=on_startup,
    )
)
