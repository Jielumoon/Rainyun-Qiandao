"""同步 cron 文件。"""

from __future__ import annotations

import logging
import os
import sys

from rainyun.data.store import DataStore
from rainyun.scheduler.cron import write_cron_file

logger = logging.getLogger(__name__)


def main() -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    try:
        store = DataStore()
        data = store.load()
        normalized = write_cron_file(data.settings.cron_schedule)
        logger.info("cron 计划已同步: %s", normalized)
        return 0
    except Exception as exc:
        logger.exception("cron 同步失败: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
