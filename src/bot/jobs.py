import logging
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import db
from src.db.repositories.calendars import CalendarRepository
from src.modules.calendar.service import CalendarService

logger = logging.getLogger(__name__)


async def sync_all_url_calendars() -> None:
    logger.info("Starting background sync for all URL calendars...")
    
    async with db.session_factory() as session:
        cal_repo = CalendarRepository(session)
        service = CalendarService(session)
        
        calendars = await cal_repo.get_all_url_calendars()
        
        for cal in calendars:
            try:
                logger.info(f"Syncing calendar {cal['id']} ({cal['name']})")
                await service.sync_calendar(cal)
                # Commit after each calendar to avoid massive transactions
                await session.commit()
            except Exception as e:
                logger.error(f"Failed to sync background calendar {cal['id']}: {e}")
                # Rollback and continue with next calendar
                await session.rollback()
                
    logger.info("Background sync finished.")
