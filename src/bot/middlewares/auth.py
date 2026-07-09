from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware

from src.db.database import db
from src.db.repositories.users import UserRepository


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        
        is_premium = False
        
        if user:
            async with db.session_factory() as session:
                repo = UserRepository(session)
                db_user = await repo.get_by_telegram_id(user.id)
                
                if db_user:
                    is_premium = await repo.is_premium(db_user["id"])
                    
                    # Auto-downgrade expired premium
                    if db_user["role"] == "premium" and not is_premium:
                        await repo.remove_premium(db_user["id"])
                        await session.commit()
                        
            data["is_premium"] = is_premium
            
        return await handler(event, data)
