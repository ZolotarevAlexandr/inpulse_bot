import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.schema import users


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> dict | None:
        stmt = select(users).where(users.c.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        row = result.mappings().first()
        return dict(row) if row else None

    async def get_by_id(self, user_id: int) -> dict | None:
        stmt = select(users).where(users.c.id == user_id)
        result = await self.session.execute(stmt)
        row = result.mappings().first()
        return dict(row) if row else None

    async def create_user(
        self, telegram_id: int, username: str | None = None, first_name: str | None = None
    ) -> dict:
        stmt = (
            users.insert()
            .values(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            .returning(users)
        )
        result = await self.session.execute(stmt)
        return dict(result.mappings().first())

    async def update_ical_url(self, user_id: int, ical_url: str) -> None:
        stmt = update(users).where(users.c.id == user_id).values(ical_url=ical_url)
        await self.session.execute(stmt)

    async def update_working_hours(self, user_id: int, start_hour: int, end_hour: int) -> None:
        stmt = update(users).where(users.c.id == user_id).values(
            work_start_hour=start_hour, work_end_hour=end_hour
        )
        await self.session.execute(stmt)
        
    async def update_last_synced(self, user_id: int) -> None:
        stmt = update(users).where(users.c.id == user_id).values(
            ical_last_synced=datetime.datetime.now()
        )
        await self.session.execute(stmt)
