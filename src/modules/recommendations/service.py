import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.recommendation_log import RecommendationLogRepository
from src.modules.calendar.service import CalendarService
from src.modules.recommendations.engine import generate_explanation, score_task
from src.modules.recommendations.models import Recommendation
from src.modules.tasks.service import TaskService

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.calendar_service = CalendarService(session)
        self.task_service = TaskService(session)
        self.log_repo = RecommendationLogRepository(session)

    async def get_recommendation(self, user_id: int) -> Recommendation | None:
        """
        Generates a task recommendation for the current free window.
        Returns None if no free window is active or no suitable tasks are found.
        """
        # Ensure calendar is somewhat fresh (e.g. sync if not synced recently)
        # For MVP, we can just sync it every time or rely on a background job.
        # Let's try to sync, if it fails, we continue with existing data.
        try:
            await self.calendar_service.sync_all_for_user(user_id)
        except Exception as e:
            logger.warning(f"Failed to sync calendar for user {user_id}: {e}")

        # Get current window
        window = await self.calendar_service.get_current_window(user_id)
        if not window:
            return None

        # Get pending tasks
        tasks = await self.task_service.list_pending_tasks(user_id)
        if not tasks:
            return None

        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

        # Score tasks
        scored_tasks = []
        for task in tasks:
            score = score_task(task, window, now)
            if score >= 0:
                scored_tasks.append((score, task))

        if not scored_tasks:
            return None

        # Sort by score descending
        scored_tasks.sort(key=lambda x: x[0], reverse=True)
        best_score, best_task = scored_tasks[0]

        # Generate explanation
        explanation = await generate_explanation(best_task, window)

        # Log recommendation
        log_id = await self.log_repo.log_recommendation(
            user_id=user_id,
            task_id=best_task.id,
            window_start=window.start,
            window_end=window.end,
        )

        # We can append log_id to explanation or return it as part of Recommendation if needed for tracking
        # For simplicity, we just return it but we don't strictly need it in the object for now
        # Actually, adding log_id to Recommendation would be good for tracking acceptance
        
        return Recommendation(
            task=best_task,
            window=window,
            score=best_score,
            explanation=explanation
        )

    async def mark_accepted(self, log_id: int) -> None:
        await self.log_repo.update_acceptance(log_id, True)

    async def mark_completed(self, log_id: int) -> None:
        await self.log_repo.update_completion(log_id, True)
