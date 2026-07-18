import datetime
from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.schema import (
    calendar_events,
    calendars,
    recommendation_log,
    tasks,
    users,
)


@dataclass
class Statistics:
    # Users
    total_users: int
    new_users_today: int
    new_users_7d: int
    new_users_30d: int
    premium_users: int
    free_users: int

    # Tasks
    total_tasks: int
    active_tasks: int
    completed_tasks: int
    completed_today: int
    completed_7d: int
    avg_tasks_per_user: float

    # Calendars
    total_calendars: int
    url_calendars: int
    file_calendars: int
    total_events: int
    users_with_calendars: int

    # Recommendations
    total_recommendations: int
    recommendations_today: int
    recommendations_7d: int
    recommendations_30d: int
    avg_recommendations_per_user: float
    acceptance_rate: float | None
    rejection_rate: float | None
    completion_rate: float | None
    avg_response_minutes: float | None


class StatisticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def collect(self) -> Statistics:
        now = datetime.datetime.now()
        today_start = datetime.datetime.combine(now.date(), datetime.time.min)
        week_ago = now - datetime.timedelta(days=7)
        month_ago = now - datetime.timedelta(days=30)

        # ── Users ──────────────────────────────────────────
        total_users = await self._scalar(select(func.count(users.c.id)))

        new_users_today = await self._scalar(
            select(func.count(users.c.id)).where(users.c.created_at >= today_start)
        )
        new_users_7d = await self._scalar(
            select(func.count(users.c.id)).where(users.c.created_at >= week_ago)
        )
        new_users_30d = await self._scalar(
            select(func.count(users.c.id)).where(users.c.created_at >= month_ago)
        )
        premium_users = await self._scalar(
            select(func.count(users.c.id)).where(
                users.c.role == "premium",
                users.c.premium_until >= now,
            )
        )
        free_users = total_users - premium_users

        # ── Tasks ──────────────────────────────────────────
        total_tasks = await self._scalar(select(func.count(tasks.c.id)))

        active_tasks = await self._scalar(
            select(func.count(tasks.c.id)).where(
                tasks.c.status.in_(["pending", "in_progress"])
            )
        )
        completed_tasks = await self._scalar(
            select(func.count(tasks.c.id)).where(tasks.c.status == "done")
        )
        completed_today = await self._scalar(
            select(func.count(tasks.c.id)).where(
                tasks.c.status == "done",
                tasks.c.completed_at >= today_start,
            )
        )
        completed_7d = await self._scalar(
            select(func.count(tasks.c.id)).where(
                tasks.c.status == "done",
                tasks.c.completed_at >= week_ago,
            )
        )
        avg_tasks_per_user = round(total_tasks / total_users, 1) if total_users else 0.0

        # ── Calendars ─────────────────────────────────────
        total_calendars = await self._scalar(select(func.count(calendars.c.id)))

        url_calendars = await self._scalar(
            select(func.count(calendars.c.id)).where(calendars.c.type == "url")
        )
        file_calendars = await self._scalar(
            select(func.count(calendars.c.id)).where(calendars.c.type == "file")
        )
        total_events = await self._scalar(select(func.count(calendar_events.c.id)))

        users_with_calendars = await self._scalar(
            select(func.count(func.distinct(calendars.c.user_id)))
        )

        # ── Recommendations ───────────────────────────────
        total_recommendations = await self._scalar(
            select(func.count(recommendation_log.c.id))
        )
        recommendations_today = await self._scalar(
            select(func.count(recommendation_log.c.id)).where(
                recommendation_log.c.shown_at >= today_start
            )
        )
        recommendations_7d = await self._scalar(
            select(func.count(recommendation_log.c.id)).where(
                recommendation_log.c.shown_at >= week_ago
            )
        )
        recommendations_30d = await self._scalar(
            select(func.count(recommendation_log.c.id)).where(
                recommendation_log.c.shown_at >= month_ago
            )
        )

        # Avg recommendations per user (only users who received at least one)
        users_with_recs = await self._scalar(
            select(func.count(func.distinct(recommendation_log.c.user_id)))
        )
        avg_recommendations_per_user = (
            round(total_recommendations / users_with_recs, 1)
            if users_with_recs
            else 0.0
        )

        # Acceptance rate: accepted / responded (where accepted IS NOT NULL)
        responded_count = await self._scalar(
            select(func.count(recommendation_log.c.id)).where(
                recommendation_log.c.accepted.is_not(None)
            )
        )
        accepted_count = await self._scalar(
            select(func.count(recommendation_log.c.id)).where(
                recommendation_log.c.accepted.is_(True)
            )
        )
        acceptance_rate = (
            round(accepted_count / responded_count * 100, 1)
            if responded_count
            else None
        )

        # Rejection rate: rejected / responded
        rejected_count = responded_count - accepted_count
        rejection_rate = (
            round(rejected_count / responded_count * 100, 1)
            if responded_count
            else None
        )

        # Completion rate: completed / accepted
        completed_recs = await self._scalar(
            select(func.count(recommendation_log.c.id)).where(
                recommendation_log.c.completed.is_(True)
            )
        )
        completion_rate = (
            round(completed_recs / accepted_count * 100, 1)
            if accepted_count
            else None
        )

        # Avg response time: difference between window_start and shown_at
        # (approximation — window_start is when the user's free slot begins)
        avg_response_result = await self.session.execute(
            select(
                func.avg(
                    func.extract(
                        "epoch",
                        recommendation_log.c.window_start
                        - recommendation_log.c.shown_at,
                    )
                )
            ).where(recommendation_log.c.accepted.is_not(None))
        )
        avg_response_seconds = avg_response_result.scalar_one()
        avg_response_minutes = (
            round(abs(avg_response_seconds) / 60, 1)
            if avg_response_seconds is not None
            else None
        )

        return Statistics(
            total_users=total_users,
            new_users_today=new_users_today,
            new_users_7d=new_users_7d,
            new_users_30d=new_users_30d,
            premium_users=premium_users,
            free_users=free_users,
            total_tasks=total_tasks,
            active_tasks=active_tasks,
            completed_tasks=completed_tasks,
            completed_today=completed_today,
            completed_7d=completed_7d,
            avg_tasks_per_user=avg_tasks_per_user,
            total_calendars=total_calendars,
            url_calendars=url_calendars,
            file_calendars=file_calendars,
            total_events=total_events,
            users_with_calendars=users_with_calendars,
            total_recommendations=total_recommendations,
            recommendations_today=recommendations_today,
            recommendations_7d=recommendations_7d,
            recommendations_30d=recommendations_30d,
            avg_recommendations_per_user=avg_recommendations_per_user,
            acceptance_rate=acceptance_rate,
            rejection_rate=rejection_rate,
            completion_rate=completion_rate,
            avg_response_minutes=avg_response_minutes,
        )

    async def _scalar(self, stmt) -> int:
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0
