import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.tasks import TaskRepository
from src.modules.tasks.models import Task


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TaskRepository(session)

    async def create_task(
        self,
        user_id: int,
        title: str,
        priority: int,
        estimated_minutes: int,
        deadline: datetime.datetime | None = None,
    ) -> Task:
        data = await self.repo.create_task(user_id, title, priority, estimated_minutes, deadline)
        return Task.from_dict(data)

    async def list_pending_tasks(self, user_id: int) -> list[Task]:
        data_list = await self.repo.list_pending_tasks(user_id)
        return [Task.from_dict(d) for d in data_list]

    async def get_task(self, task_id: int, user_id: int) -> Task | None:
        data = await self.repo.get_task(task_id, user_id)
        return Task.from_dict(data) if data else None

    async def update_task(self, task_id: int, user_id: int, **fields) -> Task | None:
        data = await self.repo.update_task(task_id, user_id, **fields)
        return Task.from_dict(data) if data else None

    async def delete_task(self, task_id: int, user_id: int) -> bool:
        return await self.repo.delete_task(task_id, user_id)

    async def mark_done(self, task_id: int, user_id: int) -> Task | None:
        data = await self.repo.mark_done(task_id, user_id)
        return Task.from_dict(data) if data else None
