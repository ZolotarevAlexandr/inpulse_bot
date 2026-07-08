import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Table,
    Text,
)

metadata = MetaData()


users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("telegram_id", BigInteger, unique=True, nullable=False),
    Column("username", String(64), nullable=True),
    Column("first_name", String(128), nullable=True),
    Column("timezone", String(64), nullable=False, default="Europe/Moscow"),
    Column("work_start_hour", Integer, nullable=False, default=8),
    Column("work_end_hour", Integer, nullable=False, default=23),
    Column("role", String(16), nullable=False, default="free"),
    Column("premium_until", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=False, default=datetime.datetime.now),
)


calendars = Table(
    "calendars",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("name", String(128), nullable=False),
    Column("type", String(16), nullable=False),  # "url" or "file"
    Column("source", Text, nullable=False),      # URL string or raw .ics file content
    Column("last_synced", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=False, default=datetime.datetime.now),
)

calendar_events = Table(
    "calendar_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("calendar_id", Integer, ForeignKey("calendars.id", ondelete="CASCADE"), nullable=False),
    Column("uid", String(512), nullable=False),
    Column("summary", String(512), nullable=False),
    Column("start_time", DateTime, nullable=False),
    Column("end_time", DateTime, nullable=False),
    Column("is_all_day", Boolean, nullable=False, default=False),
)


tasks = Table(
    "tasks",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("title", String(256), nullable=False),
    Column("deadline", DateTime, nullable=True),
    Column("priority", SmallInteger, nullable=False, default=3),
    Column("estimated_minutes", Integer, nullable=False),
    Column("status", String(16), nullable=False, default="pending"),
    Column("created_at", DateTime, nullable=False, default=datetime.datetime.now),
    Column("completed_at", DateTime, nullable=True),
)


recommendation_log = Table(
    "recommendation_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True),
    Column("window_start", DateTime, nullable=False),
    Column("window_end", DateTime, nullable=False),
    Column("shown_at", DateTime, nullable=False, default=datetime.datetime.now),
    Column("accepted", Boolean, nullable=True),
    Column("completed", Boolean, nullable=True),
)
