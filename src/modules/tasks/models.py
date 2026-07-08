import datetime
from dataclasses import dataclass
from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


@dataclass
class Task:
    id: int
    user_id: int
    title: str
    deadline: datetime.datetime | None
    priority: int
    estimated_minutes: int
    status: TaskStatus
    created_at: datetime.datetime
    completed_at: datetime.datetime | None

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            title=data["title"],
            deadline=data["deadline"],
            priority=data["priority"],
            estimated_minutes=data["estimated_minutes"],
            status=TaskStatus(data["status"]),
            created_at=data["created_at"],
            completed_at=data["completed_at"],
        )
