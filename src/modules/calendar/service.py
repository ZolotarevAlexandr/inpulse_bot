import datetime
import logging
from typing import List, Optional

import aiohttp
import pytz
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.calendar_events import CalendarEventRepository
from src.db.repositories.calendars import CalendarRepository
from src.db.repositories.users import UserRepository
from src.modules.calendar.ical_parser import parse_ical_data
from src.modules.calendar.models import FreeWindow

logger = logging.getLogger(__name__)


class CalendarService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cal_repo = CalendarRepository(session)
        self.event_repo = CalendarEventRepository(session)
        self.user_repo = UserRepository(session)

    async def add_url_calendar(self, user_id: int, name: str, url: str) -> dict:
        calendar = await self.cal_repo.create_calendar(user_id, name, "url", url)
        await self.sync_calendar(calendar)
        return calendar

    async def add_file_calendar(self, user_id: int, name: str, file_content: bytes) -> dict:
        # Save bytes as text/utf-8 or decode. .ics is usually utf-8
        content_str = file_content.decode("utf-8")
        calendar = await self.cal_repo.create_calendar(user_id, name, "file", content_str)
        await self.sync_calendar(calendar)
        return calendar

    async def delete_calendar(self, calendar_id: int, user_id: int) -> bool:
        return await self.cal_repo.delete_calendar(calendar_id, user_id)

    async def sync_all_for_user(self, user_id: int) -> int:
        calendars = await self.cal_repo.get_calendars_for_user(user_id)
        total_events = 0
        for cal in calendars:
            try:
                events_count = await self.sync_calendar(cal)
                total_events += events_count
            except Exception as e:
                logger.error(f"Failed to sync calendar {cal['id']}: {e}")
        return total_events

    async def sync_calendar(self, calendar: dict) -> int:
        now = datetime.datetime.now(datetime.timezone.utc)
        start_date = now.date()
        end_date = start_date + datetime.timedelta(days=30)

        ical_data = b""
        if calendar["type"] == "url":
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(calendar["source"], timeout=10) as resp:
                        resp.raise_for_status()
                        ical_data = await resp.read()
                except Exception as e:
                    logger.error(f"Failed to fetch iCal URL {calendar['source']}: {e}")
                    raise ValueError(f"Failed to fetch calendar {calendar['name']}") from e
        elif calendar["type"] == "file":
            ical_data = calendar["source"].encode("utf-8")

        events = parse_ical_data(ical_data, start_date, end_date)
        
        events_dicts = [
            {
                "uid": e.uid,
                "summary": e.summary,
                "start_time": e.start_time,
                "end_time": e.end_time,
                "is_all_day": e.is_all_day
            }
            for e in events
        ]
        
        await self.event_repo.bulk_upsert(calendar["id"], events_dicts)
        await self.cal_repo.update_last_synced(calendar["id"])
        
        return len(events_dicts)

    async def get_free_windows(self, user_id: int, target_date: datetime.date) -> List[FreeWindow]:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
            
        tz = pytz.timezone(user.get("timezone", "Europe/Moscow"))
        
        start_time_local = datetime.datetime.combine(target_date, datetime.time(user.get("work_start_hour", 8), 0))
        end_time_local = datetime.datetime.combine(target_date, datetime.time(user.get("work_end_hour", 23), 0))
        
        start_time_utc = tz.localize(start_time_local).astimezone(datetime.timezone.utc).replace(tzinfo=None)
        end_time_utc = tz.localize(end_time_local).astimezone(datetime.timezone.utc).replace(tzinfo=None)
        
        events = await self.event_repo.get_events_in_range_for_user(user_id, start_time_utc, end_time_utc)
        
        active_events = []
        for e in events:
            if e["is_all_day"]:
                continue
            event_start = max(e["start_time"], start_time_utc)
            event_end = min(e["end_time"], end_time_utc)
            if event_start < event_end:
                active_events.append((event_start, event_end, e["summary"]))
                
        active_events.sort(key=lambda x: x[0])
        merged = []
        for e in active_events:
            if not merged:
                merged.append(e)
            else:
                last = merged[-1]
                if e[0] <= last[1]:
                    merged[-1] = (last[0], max(last[1], e[1]), last[2])
                else:
                    merged.append(e)
                    
        windows = []
        current_time = start_time_utc
        for e in merged:
            if current_time < e[0]:
                duration = int((e[0] - current_time).total_seconds() / 60)
                if duration >= 20:
                    windows.append(FreeWindow(start=current_time, end=e[0], duration_minutes=duration, next_event_name=e[2]))
            current_time = max(current_time, e[1])
            
        if current_time < end_time_utc:
            duration = int((end_time_utc - current_time).total_seconds() / 60)
            if duration >= 20:
                windows.append(FreeWindow(start=current_time, end=end_time_utc, duration_minutes=duration, next_event_name="End of workday"))
                
        # Convert UTC back to local timezone for display
        for w in windows:
            w.start = pytz.utc.localize(w.start).astimezone(tz).replace(tzinfo=None)
            w.end = pytz.utc.localize(w.end).astimezone(tz).replace(tzinfo=None)

        return windows

    async def get_current_window(self, user_id: int) -> Optional[FreeWindow]:
        now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None
            
        tz = pytz.timezone(user.get("timezone", "Europe/Moscow"))
        local_now = pytz.utc.localize(now_utc).astimezone(tz).replace(tzinfo=None)
        
        start_time_local = datetime.datetime.combine(local_now.date(), datetime.time(user.get("work_start_hour", 8), 0))
        end_time_local = datetime.datetime.combine(local_now.date(), datetime.time(user.get("work_end_hour", 23), 0))
        
        if local_now >= end_time_local:
            return None
            
        effective_start = max(local_now, start_time_local)
        
        start_time_utc = tz.localize(start_time_local).astimezone(datetime.timezone.utc).replace(tzinfo=None)
        end_time_utc = tz.localize(end_time_local).astimezone(datetime.timezone.utc).replace(tzinfo=None)
        
        events = await self.event_repo.get_events_in_range_for_user(user_id, start_time_utc, end_time_utc)
        
        next_event_start = end_time_local
        next_event_name = "End of workday"
        current_event_name = None
        
        # Sort events by start time
        events.sort(key=lambda x: x["start_time"])
        
        for e in events:
            if e["is_all_day"]:
                continue
            e_start_local = pytz.utc.localize(e["start_time"]).astimezone(tz).replace(tzinfo=None)
            e_end_local = pytz.utc.localize(e["end_time"]).astimezone(tz).replace(tzinfo=None)
            
            if e_start_local <= local_now < e_end_local:
                current_event_name = e["summary"]
                
            if e_start_local > local_now and e_start_local < next_event_start:
                next_event_start = e_start_local
                next_event_name = e["summary"]
                
        duration = int((next_event_start - local_now).total_seconds() / 60)
        
        if duration >= 10:
            return FreeWindow(
                start=local_now, 
                end=next_event_start, 
                duration_minutes=duration, 
                next_event_name=next_event_name,
                current_event_name=current_event_name
            )
            
        return None
