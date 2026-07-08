import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.schema import tasks


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_task(
        self,
        user_id: int,
        title: str,
        priority: int,
        estimated_minutes: int,
        deadline: datetime.datetime | None = None,
    ) -> dict:
        stmt = (
            tasks.insert()
            .values(
                user_id=user_id,
                title=title,
                priority=priority,
                estimated_minutes=estimated_minutes,
                deadline=deadline,
            )
            .returning(tasks)
        )
        result = await self.session.execute(stmt)
        return dict(result.mappings().first())

    async def list_pending_tasks(self, user_id: int) -> list[dict]:
        stmt = (
            select(tasks)
            .where(tasks.c.user_id == user_id)
            .where(tasks.c.status.in_(["pending", "in_progress"]))
            .order_by(tasks.c.priority.desc(), tasks.c.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [dict(r) for r in result.mappings().all()]

    async def get_task(self, task_id: int, user_id: int) -> dict | None:
        stmt = select(tasks).where(tasks.c.id == task_id, tasks.c.user_id == user_id)
        result = await self.session.execute(stmt)
        row = result.mappings().first()
        return dict(row) if row else None

    async def update_task(self, task_id: int, user_id: int, **fields) -> dict | None:
        stmt = (
            update(tasks)
            .where(tasks.c.id == task_id, tasks.c.user_id == user_id)
            .values(**fields)
            .returning(tasks)
        )
        result = await self.session.execute(stmt)
        row = result.mappings().first()
        return dict(row) if row else None

    async def delete_task(self, task_id: int, user_id: int) -> bool:
        stmt = delete(tasks).where(tasks.c.id == task_id, tasks.c.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def mark_done(self, task_id: int, user_id: int) -> dict | None:
        return await self.update_task(
            task_id,
            user_id,
            status="done",
            completed_at=datetime.datetime.now(),
        )
