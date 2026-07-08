from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.schema import whitelisted_users


class WhitelistRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_whitelisted(self, telegram_id: int) -> bool:
        stmt = select(whitelisted_users).where(whitelisted_users.c.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.first() is not None

    async def add_to_whitelist(self, telegram_id: int, added_by: int | None = None) -> None:
        # Upsert equivalent could be used if PostgreSQL supports it, but for simplicity we can insert if not exists
        if not await self.is_whitelisted(telegram_id):
            stmt = whitelisted_users.insert().values(telegram_id=telegram_id, added_by=added_by)
            await self.session.execute(stmt)

    async def remove_from_whitelist(self, telegram_id: int) -> None:
        stmt = delete(whitelisted_users).where(whitelisted_users.c.telegram_id == telegram_id)
        await self.session.execute(stmt)

    async def list_whitelisted_users(self) -> list[int]:
        stmt = select(whitelisted_users.c.telegram_id).order_by(whitelisted_users.c.added_at.desc())
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]
