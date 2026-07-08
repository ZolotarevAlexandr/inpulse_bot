import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.schema import recommendation_log


class RecommendationLogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_recommendation(
        self, user_id: int, task_id: int | None, window_start: datetime.datetime, window_end: datetime.datetime
    ) -> int:
        stmt = (
            recommendation_log.insert()
            .values(
                user_id=user_id,
                task_id=task_id,
                window_start=window_start,
                window_end=window_end,
            )
            .returning(recommendation_log.c.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update_acceptance(self, log_id: int, accepted: bool) -> None:
        stmt = update(recommendation_log).where(recommendation_log.c.id == log_id).values(accepted=accepted)
        await self.session.execute(stmt)

    async def update_completion(self, log_id: int, completed: bool) -> None:
        stmt = update(recommendation_log).where(recommendation_log.c.id == log_id).values(completed=completed)
        await self.session.execute(stmt)
