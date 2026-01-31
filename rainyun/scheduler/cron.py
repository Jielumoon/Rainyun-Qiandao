"""cron 配置写入与校验。"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_SCHEDULE = "0 8 * * *"
VALID_AT_EXPRESSIONS = {
    "@yearly",
    "@annually",
    "@monthly",
    "@weekly",
    "@daily",
    "@hourly",
}

CRON_FILE_PATH = os.environ.get("CRON_FILE_PATH", "/etc/cron.d/rainyun")
CRON_USER = os.environ.get("CRON_USER", "root")
CRON_COMMAND = os.environ.get(
    "CRON_COMMAND",
    "cd /app && /usr/local/bin/python -u -m rainyun.scheduler.cron_runner",
)

_CRON_BASIC_PATTERN = re.compile(r"^([0-9*/,-]+\s+){4}[0-9*/,-]+$")


def _resolve_log_path(path_value: str, fallback: str) -> str:
    try:
        if Path(path_value).exists():
            return path_value
    except Exception:
        pass
    return fallback


def normalize_schedule(value: str | None) -> str:
    raw = (value or "").strip().strip("\"'").strip()
    if not raw:
        return DEFAULT_SCHEDULE

    raw = raw.splitlines()[0].strip()
    if not raw:
        return DEFAULT_SCHEDULE

    if raw.startswith("@"):
        if raw in VALID_AT_EXPRESSIONS:
            return raw
        logger.warning("非法 @cron 表达式: %s，回退默认值", raw)
        return DEFAULT_SCHEDULE

    if not _CRON_BASIC_PATTERN.match(raw):
        logger.warning("cron 表达式格式无效: %s，回退默认值", raw)
        return DEFAULT_SCHEDULE

    return raw


def build_cron_content(schedule: str) -> str:
    stdout_path = _resolve_log_path(os.environ.get("CRON_STDOUT", "/proc/1/fd/1"), "/dev/stdout")
    stderr_path = _resolve_log_path(os.environ.get("CRON_STDERR", "/proc/1/fd/2"), "/dev/stderr")
    command = f"{CRON_COMMAND} >>{stdout_path} 2>>{stderr_path}"
    lines = [
        "SHELL=/bin/sh",
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        f"{schedule} {CRON_USER} {command}",
        "",
    ]
    return "\n".join(lines)


def write_cron_file(schedule: str | None, path: str | None = None) -> str:
    target = Path(path or CRON_FILE_PATH)
    normalized = normalize_schedule(schedule)
    content = build_cron_content(normalized)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    try:
        os.chmod(target, 0o644)
    except Exception as exc:
        logger.warning("设置 cron 文件权限失败: %s", exc)
    return normalized
