import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
REPORTS_DIR = BASE_DIR / "reports"
LOG_FILE = BASE_DIR / "report_generator.log"

# Читаем настройки из файла .env (значения из .env главнее системных переменных)
load_dotenv(BASE_DIR / ".env", override=True)


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    log_level: str
    max_input_chars: int


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("your_"):
        raise RuntimeError(f"Не заполнена переменная {name}. Проверь файл .env.")
    return value


def _parse_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if minimum <= value <= maximum else default


def load_settings() -> Settings:
    return Settings(
        api_key=_require("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip(),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip(),
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        max_input_chars=_parse_int("MAX_INPUT_CHARS", 60000, 1000, 200000),
    )