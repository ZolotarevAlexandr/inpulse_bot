import datetime
from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.schema import calendars


class CalendarRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_calendar(self, user_id: int, name: str, type_: str, source: str) -> dict:
        stmt = (
            calendars.insert()
            .values(
                user_id=user_id,
                name=name,
                type=type_,
                source=source,
            )
            .returning(calendars)
        )
        result = await self.session.execute(stmt)
        return dict(result.mappings().first())

    async def get_calendars_for_user(self, user_id: int) -> list[dict]:
        stmt = select(calendars).where(calendars.c.user_id == user_id).order_by(calendars.c.created_at.asc())
        result = await self.session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]

    async def get_all_url_calendars(self) -> list[dict]:
        stmt = select(calendars).where(calendars.c.type == "url")
        result = await self.session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]

    async def update_last_synced(self, calendar_id: int) -> None:
        stmt = update(calendars).where(calendars.c.id == calendar_id).values(last_synced=datetime.datetime.now())
        await self.session.execute(stmt)

    async def delete_calendar(self, calendar_id: int, user_id: int) -> bool:
        stmt = delete(calendars).where(calendars.c.id == calendar_id, calendars.c.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
