import datetime
from dataclasses import dataclass


@dataclass
class CalendarEvent:
    uid: str
    summary: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    is_all_day: bool

    @classmethod
    def from_dict(cls, data: dict) -> "CalendarEvent":
        return cls(
            uid=data["uid"],
            summary=data["summary"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            is_all_day=data.get("is_all_day", False),
        )


@dataclass
class FreeWindow:
    start: datetime.datetime
    end: datetime.datetime
    duration_minutes: int
    next_event_name: str | None = None
    current_event_name: str | None = None
