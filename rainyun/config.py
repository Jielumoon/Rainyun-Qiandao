"""配置定义与解析。"""

import logging
import os

logger = logging.getLogger(__name__)


def _read_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid config: {name} must be int, using default {default}")
        return default


def _read_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning(f"Invalid config: {name} must be number, using default {default}")
        return default


def _read_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.lower() in ("true", "1", "yes")


APP_BASE_URL = os.environ.get("APP_BASE_URL", "https://app.rainyun.com").rstrip("/")
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.v2.rainyun.com").rstrip("/")
APP_VERSION = os.environ.get("APP_VERSION", "2.5")
COOKIE_FILE = os.environ.get("COOKIE_FILE", "cookies.json")

POINTS_TO_CNY_RATE = _read_int("POINTS_TO_CNY_RATE", 2000)
CAPTCHA_RETRY_LIMIT = _read_int("CAPTCHA_RETRY_LIMIT", 5)
CAPTCHA_RETRY_UNLIMITED = _read_bool("CAPTCHA_RETRY_UNLIMITED", False)

REQUEST_TIMEOUT = _read_int("REQUEST_TIMEOUT", 15)
MAX_RETRIES = _read_int("MAX_RETRIES", 3)
RETRY_DELAY = _read_float("RETRY_DELAY", 2)

DOWNLOAD_TIMEOUT = _read_int("DOWNLOAD_TIMEOUT", 10)
DOWNLOAD_MAX_RETRIES = _read_int("DOWNLOAD_MAX_RETRIES", 3)
DOWNLOAD_RETRY_DELAY = _read_float("DOWNLOAD_RETRY_DELAY", 2)

# Chrome 低内存模式（适用于 1核1G 小鸡）
CHROME_LOW_MEMORY = _read_bool("CHROME_LOW_MEMORY", False)

DEFAULT_RENEW_COST_7_DAYS = _read_int("DEFAULT_RENEW_COST_7_DAYS", 2258)
