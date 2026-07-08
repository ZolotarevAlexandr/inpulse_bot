from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from src.config import settings
from src.db.database import db
from src.db.repositories.whitelist import WhitelistRepository


class WhitelistMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        
        if user:
            # Check if user is admin
            if user.id in settings.telegram_bot.admins:
                return await handler(event, data)
                
            # Check database whitelist
            async with db.session_factory() as session:
                repo = WhitelistRepository(session)
                is_whitelisted = await repo.is_whitelisted(user.id)
                
            if not is_whitelisted:
                if isinstance(event, Message):
                    await event.answer("⛔ Access is restricted. Please contact the administrator to get whitelisted.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⛔ Access is restricted.", show_alert=True)
                return
            
        return await handler(event, data)
