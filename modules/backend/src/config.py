import os
from pathlib import Path


def _load_env():
    """Silently populate os.environ from root .env if present and not already set."""
    # Find project root (4 levels up from modules/backend/src/config.py)
    root = Path(__file__).resolve().parent.parent.parent.parent
    env_file = root / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


_load_env()


class Settings:
    app_name: str = os.getenv("APP_NAME", "Shikshak AI Backend")
    api_v1_str: str = os.getenv("API_V1_STR", "/api/v1")


settings = Settings()

