import datetime
import logging
from typing import List

import recurring_ical_events
from icalendar import Calendar

from src.modules.calendar.models import CalendarEvent

logger = logging.getLogger(__name__)


def parse_ical_data(ical_data: bytes, start_date: datetime.date, end_date: datetime.date) -> List[CalendarEvent]:
    """
    Parses raw iCal bytes, expanding recurring events between start_date and end_date.
    Returns a list of CalendarEvent domain models.
    """
    try:
        cal = Calendar.from_ical(ical_data)
        
        events = recurring_ical_events.of(cal).between(start_date, end_date)
        
        parsed_events = []
        for component in events:
            if component.name != "VEVENT":
                continue
                
            uid = str(component.get("uid", ""))
            summary = str(component.get("summary", "Busy"))
            dtstart = component.get("dtstart")
            dtend = component.get("dtend")

            if not dtstart or not dtend:
                continue

            start = dtstart.dt
            end = dtend.dt
            
            is_all_day = False
            if type(start) is datetime.date:
                is_all_day = True
                start = datetime.datetime.combine(start, datetime.time.min, tzinfo=datetime.timezone.utc)
                if type(end) is datetime.date:
                    end = datetime.datetime.combine(end, datetime.time.min, tzinfo=datetime.timezone.utc)
            
            if hasattr(start, "astimezone"):
                start = start.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            if hasattr(end, "astimezone"):
                end = end.astimezone(datetime.timezone.utc).replace(tzinfo=None)

            parsed_events.append(CalendarEvent(
                uid=uid,
                summary=summary,
                start_time=start,
                end_time=end,
                is_all_day=is_all_day
            ))
            
        return parsed_events

    except Exception as e:
        logger.error(f"Failed to parse iCal data: {e}")
        raise ValueError("Failed to parse calendar data") from e
