
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Cancel, Column, SwitchTo
from aiogram_dialog.widgets.text import Const, Format, Multi

from src.bot.states import AccountSG
from src.config import settings
from src.db.database import db
from src.db.repositories.users import UserRepository


async def account_getter(dialog_manager: DialogManager, **kwargs):
    user_id = dialog_manager.event.from_user.id
    is_premium = dialog_manager.middleware_data.get("is_premium", False)
    
    tasks_used = 0
    recs_used = 0
    
    async with db.session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(user_id)
        
        premium_until = "N/A"
        if user:
            if user.get("premium_until"):
                premium_until = user["premium_until"].strftime("%d.%m.%Y")
                
            if not is_premium:
                from src.db.repositories.recommendation_log import RecommendationLogRepository
                from src.modules.tasks.service import TaskService
                
                task_service = TaskService(session)
                pending = await task_service.list_pending_tasks(user["id"])
                tasks_used = len(pending)
                
                log_repo = RecommendationLogRepository(session)
                recs_used = await log_repo.get_recommendations_today_count(user["id"])
            
    return {
        "is_premium": is_premium,
        "premium_until": premium_until,
        "tasks_used": tasks_used,
        "recs_used": recs_used,
        "free_tasks_limit": settings.free_limits.active_tasks,
        "free_recs_limit": settings.free_limits.recommendations_per_day,
    }


async def buy_getter(dialog_manager: DialogManager, **kwargs):
    return {
        "payment_link": settings.subscription.payment_link,
        "admin_username": settings.subscription.admin_username,
        "price_rub_month": settings.subscription.price_rub_month,
    }

dialog = Dialog(
    Window(
        Multi(
            Const("👤 <b>Account</b>\n"),
            Format("<b>Role:</b> InPulse Pro ⭐\n", when="is_premium"),
            Format("<b>Role:</b> Free\n", when=lambda data, w, m: not data.get("is_premium", False)),
            Format("<b>InPulse Pro until:</b> {premium_until}\n", when="is_premium"),
            Const(
                "You have unlimited recommendations and active tasks! 🚀\n",
                when="is_premium"
            ),
            Format(
                "<b>Limits:</b>\n"
                "• Active Tasks: {tasks_used} / {free_tasks_limit}\n"
                "• Recommendations Today: {recs_used} / {free_recs_limit}\n",
                when=lambda data, w, m: not data.get("is_premium", False)
            ),
        ),
        Column(
            SwitchTo(Const("💎 Buy InPulse Pro"), id="buy", state=AccountSG.buy, when=lambda data, w, m: not data.get("is_premium", False)),
            Cancel(Const("⬅️ Back")),
        ),
        state=AccountSG.info,
        getter=account_getter,
    ),
    Window(
        Format(
            "💳 <b>To purchase an InPulse Pro subscription ({price_rub_month} RUB/month):</b>\n\n"
        ),
        Format("1. Transfer the payment to {payment_link}\n"),
        Format("2. Send the receipt screenshot to {admin_username} in a private message\n"),
        Const("3. Your subscription will be activated shortly!"),
        SwitchTo(Const("⬅️ Back"), id="back", state=AccountSG.info),
        state=AccountSG.buy,
        getter=buy_getter,
    )
)
