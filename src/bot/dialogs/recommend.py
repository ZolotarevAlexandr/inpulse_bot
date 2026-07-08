from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Column
from aiogram_dialog.widgets.text import Const, Format

from src.bot.states import RecommendSG
from src.db.database import db
from src.db.repositories.users import UserRepository
from src.modules.recommendations.service import RecommendationService


async def recommend_getter(dialog_manager: DialogManager, **kwargs):
    user_id = dialog_manager.event.from_user.id
    async with db.session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(user_id)
        if not user:
            return {"text": "User not found."}
            
        rec_service = RecommendationService(session)
        rec = await rec_service.get_recommendation(user["id"])
        await session.commit()
        
        if rec:
            dialog_manager.dialog_data["task_id"] = rec.task.id
            return {
                "has_rec": True,
                "text": rec.explanation,
                "task_id": rec.task.id
            }
        else:
            return {
                "has_rec": False,
                "text": "No active free window right now, or no tasks that fit in your current window!"
            }


async def accept_task(call: CallbackQuery, button: Button, dialog_manager: DialogManager):
    task_id = dialog_manager.dialog_data.get("task_id")
    user_id = call.from_user.id
    # We could log acceptance here. We need log_id for that, which isn't currently returned by get_recommendation easily unless we add it.
    # For MVP, just show a message.
    await call.answer("Great! Go get it done!", show_alert=True)
    await dialog_manager.done()


dialog = Dialog(
    Window(
        Format("{text}"),
        Column(
            Button(Const("✅ Let's do it!"), id="accept", on_click=accept_task, when="has_rec"),
            Cancel(Const("⬅️ Back")),
        ),
        state=RecommendSG.show,
        getter=recommend_getter,
    )
)
