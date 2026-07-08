from enum import StrEnum
from pathlib import Path

import yaml
from aiogram.types import BotCommand
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class Environment(StrEnum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class SettingsEntityModel(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True, extra="forbid")


class LLM(SettingsEntityModel):
    """LLM settings for text generation"""
    
    api_key: SecretStr
    "API key for the LLM provider"
    base_url: str = "https://api.openai.com/v1"
    "Base URL for the LLM API"
    model: str = "gpt-4o-mini"
    "Model to use for generation"


class TelegramBot(SettingsEntityModel):
    """Telegram Bot settings"""
    
    token: SecretStr
    "Telegram bot token from @BotFather"
    admins: list[int] = []
    "Admin' telegram IDs"
    name: str | None = None
    "Desired bot name"
    description: str | None = None
    "Bot description"
    short_description: str | None = None
    "Bot short description"
    commands: list[BotCommand] | None = None
    "Bot commands (displayed in telegram menu)"


class Settings(SettingsEntityModel):
    """Settings for the application. Get settings from `settings.yaml` file."""

    schema_: str | None = Field(None, alias="$schema")
    environment: Environment = Environment.DEVELOPMENT
    "App environment flag"
    
    db_url: SecretStr = Field(
        examples=[
            "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/inpulse",
            "postgresql+asyncpg://postgres:postgres@db:5432/inpulse",
        ],
    )
    "Connection String for SQLAlchemy"
    
    redis_url: SecretStr | None = Field(None, examples=["redis://127.0.0.1:6379/0", "redis://redis:6379/0"])
    "Redis URL (for aiogram-dialog and FSM)"
    
    timezone: str = "Europe/Moscow"
    "Timezone for interpreting dates"
    
    ical_refresh_interval_minutes: int = 60
    "How often to refresh the iCal feeds (in minutes)"

    telegram_bot: TelegramBot
    "Telegram Bot configuration"

    llm: LLM | None = None
    "LLM integration settings for recommendations"

    @classmethod
    def from_yaml(cls, path: Path) -> "Settings":
        with open(path, encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f)
            yaml_config.pop("$schema", None)

        return cls.model_validate(yaml_config)

    @classmethod
    def save_schema(cls, path: Path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            schema = {"$schema": "http://json-schema.org/draft-07/schema#", **cls.model_json_schema()}
            yaml.dump(schema, f, sort_keys=False)
