import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.schema import calendar_events


class CalendarEventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def bulk_upsert(self, calendar_id: int, events: list[dict]) -> None:
        """
        Delete all future events for the calendar and insert new ones.
        """
        now = datetime.datetime.now()
        delete_stmt = delete(calendar_events).where(
            calendar_events.c.calendar_id == calendar_id, calendar_events.c.end_time >= now
        )
        await self.session.execute(delete_stmt)

        if not events:
            return

        values = []
        for e in events:
            val = e.copy()
            val["calendar_id"] = calendar_id
            values.append(val)

        await self.session.execute(calendar_events.insert(), values)

    async def get_events_in_range_for_user(
        self, user_id: int, start: datetime.datetime, end: datetime.datetime
    ) -> list[dict]:
        from src.db.schema import calendars
        
        stmt = (
            select(calendar_events)
            .select_from(calendar_events.join(calendars, calendar_events.c.calendar_id == calendars.c.id))
            .where(
                calendars.c.user_id == user_id,
                calendar_events.c.end_time >= start,
                calendar_events.c.start_time <= end,
            )
            .order_by(calendar_events.c.start_time.asc())
        )
        result = await self.session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]
