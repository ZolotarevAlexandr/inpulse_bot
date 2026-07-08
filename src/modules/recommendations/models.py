from dataclasses import dataclass

from src.modules.calendar.models import FreeWindow
from src.modules.tasks.models import Task


@dataclass
class Recommendation:
    task: Task
    window: FreeWindow
    score: float
    explanation: str
