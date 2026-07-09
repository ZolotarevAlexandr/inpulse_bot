# InPulse Bot

> Smart task recommendations for your free windows between classes.

_That's a small project created within one of elective courses_

## Features

📋 Create and manage tasks with priorities and deadlines<br/>
📆 Import your schedule from iCal (URL or file)<br/>
🪟 Automatically detect free windows in your calendar<br/>
🎯 Get smart task recommendations that fit your current free time<br/>
🤖 Optional LLM-powered motivational messages (via Ollama or any OpenAI-compatible API)<br/>
🔄 Background calendar sync on a configurable interval<br/>
👮 Whitelist & admin panel for access control<br/>

## Technologies

- [Python 3.13](https://www.python.org/downloads/) & [UV](https://docs.astral.sh/uv)
- [Aiogram 3](https://docs.aiogram.dev/en/latest/) & [aiogram-dialog](https://aiogram-dialog.readthedocs.io/)
- [SQLAlchemy 2](https://docs.sqlalchemy.org/) & [Alembic](https://alembic.sqlalchemy.org/) (PostgreSQL)
- [Redis](https://redis.io/) for FSM storage (optional, falls back to in-memory)
- [Ollama](https://ollama.ai/) / OpenAI-compatible API for LLM recommendations (optional)
- [APScheduler](https://apscheduler.readthedocs.io/) for background calendar sync
- Formatting and linting: [Ruff](https://docs.astral.sh/ruff/)
- Deployment: [Docker](https://www.docker.com/), [Docker Compose](https://docs.docker.com/compose/)

## Development

### Getting started

1. Install [Python 3.13+](https://www.python.org/downloads/), [UV](https://docs.astral.sh/uv/getting-started/installation/),
   [Docker](https://docs.docker.com/engine/install/)
2. Install project dependencies with [UV](https://docs.astral.sh/uv/concepts/projects/sync/#syncing-the-environment):
   ```bash
   uv sync
   ```
3. Start PostgreSQL and Redis (and optionally Ollama) via Docker Compose:
   ```bash
   docker compose up -d db redis
   ```
4. Copy `settings.example.yaml` to `settings.yaml` and edit as needed:
   ```bash
   cp settings.example.yaml settings.yaml
   ```
5. Run database migrations:
   ```bash
   uv run alembic upgrade head
   ```
6. Start the bot:
   ```bash
   uv run -m src.bot
   ```
   > Follow provided instructions if needed

> [!TIP]
> You can view `settings.yaml` schema in
> [config_schema.py](src/config_schema.py) and in [settings.schema.yaml](settings.schema.yaml)

### LLM Configuration

LLM integration is **optional**. If a configured LLM request fails, the bot falls back to static recommendation messages automatically.

To enable LLM-powered messages, add the `llm` section to your `settings.yaml`:

```yaml
llm:
  base_url: "http://localhost:11434/v1"  # Ollama default
  api_key: "ollama"                       # Any string for Ollama
  model: "gemma3:4b-it-qat"              # Any model pulled in Ollama
```

To use Ollama via Docker Compose:
```bash
docker compose up -d ollama
# Wait for it to start, then pull a model:
docker compose exec ollama ollama pull gemma3:4b-it-qat
```

### Deployment

We use Docker with Docker Compose plugin to run the service on servers.

1. Copy the file with settings: `cp settings.example.yaml settings.yaml`
2. Change settings in the `settings.yaml` file according to your needs
   (check [settings.schema.yaml](settings.schema.yaml) for more info)
3. Install Docker with Docker Compose
4. Build a Docker image: `docker compose build --pull`
5. Run the container: `docker compose up --detach`
6. Check the logs: `docker compose logs -f`

## How to update dependencies

1. Run `uv lock --upgrade` to update all dependencies
2. Run `uv pip list --outdated` to check for outdated dependencies
3. Run `uv add <package>@latest` to add a new dependency if needed
