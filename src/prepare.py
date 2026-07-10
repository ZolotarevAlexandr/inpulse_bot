import shutil
import webbrowser
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parents[1]
SETTINGS_TEMPLATE = BASE_DIR / "settings.example.yaml"
SETTINGS_FILE = BASE_DIR / "settings.yaml"
SETTINGS_SCHEMA = BASE_DIR / "settings.schema.yaml"
PRE_COMMIT_CONFIG = BASE_DIR / ".pre-commit-config.yaml"
BOT_FATHER_URL = "https://t.me/BotFather"


def get_settings():
    if not SETTINGS_FILE.exists():
        raise RuntimeError("❌ No `settings.yaml` found.")
    try:
        with open(SETTINGS_FILE) as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        raise RuntimeError("❌ No `settings.yaml` found.") from e


def ensure_settings_file():
    if not SETTINGS_TEMPLATE.exists():
        print("❌ No `settings.example.yaml` found. Skipping copying.")
        return

    if SETTINGS_FILE.exists():
        print("✅ `settings.yaml` exists.")
        return

    shutil.copy(SETTINGS_TEMPLATE, SETTINGS_FILE)
    print(f"✅ Copied `{SETTINGS_TEMPLATE}` to `{SETTINGS_FILE}`")


def check_and_prompt_bot_token():
    settings = get_settings()
    bot_settings = settings.get("telegram_bot", {})
    bot_token = bot_settings.get("token", None)

    if not bot_token or bot_token == "...":
        print("⚠️ `telegram_bot.token` is missing in `settings.yaml`.")
        print(f"  ➡️ Generate a token in @BotFather: {BOT_FATHER_URL}")
        webbrowser.open(BOT_FATHER_URL)
        token = input("  🔑 Please paste the generated token below (or press Enter to skip):\n  > ").strip()

        if token:
            try:
                with open(SETTINGS_FILE) as f:
                    as_text = f.read()
                as_text = as_text.replace("token: null", f"token: {token}")
                as_text = as_text.replace("token: ...", f"token: {token}")
                with open(SETTINGS_FILE, "w") as f:
                    f.write(as_text)
                print("  ✅ `telegram_bot.token` has been updated in `settings.yaml`.")
            except Exception as e:
                print(f"  ❌ Error updating `settings.yaml`: {e}")
        else:
            print("  ⚠️ Token was not provided. Please manually update `settings.yaml` later.")
    else:
        print("✅ `telegram_bot.token` is specified.")


def prepare():
    ensure_settings_file()
    check_and_prompt_bot_token()


if __name__ == "__main__":
    prepare()
