import logging

from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Start
from aiogram_dialog.widgets.text import Const, Format

from src.bot.states import AccountSG, RecommendSG
from src.config import settings
from src.db.database import db
from src.db.repositories.users import UserRepository
from src.modules.recommendations.service import RecommendationService

logger = logging.getLogger(__name__)

async def recommend_getter(dialog_manager: DialogManager, **kwargs):
    user_id = dialog_manager.event.from_user.id
    username = dialog_manager.event.from_user.username
    is_premium = dialog_manager.middleware_data.get("is_premium", False)
    
    async with db.session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(user_id)
        if not user:
            return {"text": "User not found.", "has_rec": False}
            
        if not is_premium:
            from src.db.repositories.recommendation_log import RecommendationLogRepository
            log_repo = RecommendationLogRepository(session)
            count = await log_repo.get_recommendations_today_count(user["id"])
            if count >= settings.free_limits.recommendations_per_day:
                logger.warning(f"User {user_id} (@{username}) hit Free tier limits (recommendations)")
                return {
                    "has_rec": False,
                    "is_premium": False,
                    "text": f"⭐ You've used your {settings.free_limits.recommendations_per_day} free recommendations for today. Upgrade to InPulse Pro for unlimited access!",
                }
            
        rec_service = RecommendationService(session)
        rec = await rec_service.get_recommendation(user["id"])
        await session.commit()
        
        if rec:
            dialog_manager.dialog_data["task_id"] = rec.task.id
            logger.info(f"Generated recommendation for user {user_id} (@{username}): Task {rec.task.id}")
            logger.info(f"[ANALYTICS] User {user_id} (@{username}) received recommendation for task {rec.task.id}")
            return {
                "has_rec": True,
                "is_premium": is_premium,
                "text": rec.explanation,
                "task_id": rec.task.id
            }
        else:
            logger.info(f"No tasks fit window for user {user_id} (@{username})")
            return {
                "has_rec": False,
                "is_premium": is_premium,
                "text": "No active free window right now, or no tasks that fit in your current window!"
            }


async def accept_task(call: CallbackQuery, button: Button, dialog_manager: DialogManager):
    task_id = dialog_manager.dialog_data.get("task_id")
    user_id = call.from_user.id
    username = call.from_user.username
    logger.info(f"[ANALYTICS] User {user_id} (@{username}) ACCEPTED recommendation for task {task_id}")
    await call.answer("Great! Go get it done!", show_alert=True)
    await dialog_manager.done()


dialog = Dialog(
    Window(
        Format("{text}"),
        Column(
            Button(Const("✅ Let's do it!"), id="accept", on_click=accept_task, when="has_rec"),
            Start(Const("💎 Buy InPulse Pro"), id="buy_premium", state=AccountSG.buy, when=lambda data, w, m: not data.get("is_premium", False)),
            Cancel(Const("⬅️ Back")),
        ),
        state=RecommendSG.show,
        getter=recommend_getter,
    )
)
