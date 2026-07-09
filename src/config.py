import os
import sys

from pydantic import SecretStr

from src.config_schema import Settings
from src.prepare import SETTINGS_FILE, prepare

try:
    settings = Settings.from_yaml(SETTINGS_FILE)
except (FileNotFoundError, ValueError) as e:
    print(f"Failed to load settings: {e}")
    if "--help" not in sys.argv:
        prepare()
        settings = Settings.from_yaml(SETTINGS_FILE)
    else:
        sys.exit(1)

if "DB_URL" in os.environ:
    settings.db_url = SecretStr(os.environ["DB_URL"])
