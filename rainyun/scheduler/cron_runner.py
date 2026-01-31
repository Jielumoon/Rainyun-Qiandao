"""定时任务入口（基于 DataStore）。"""

from __future__ import annotations

import logging
import os
import sys

from rainyun.data.store import DataStore
from rainyun.scheduler.runner import MultiAccountRunner

logger = logging.getLogger(__name__)


def _acquire_lock(lock_path: str) -> int | None:
    try:
        import fcntl
    except Exception:
        logger.warning("当前环境不支持文件锁，跳过防重入")
        return -1

    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except OSError:
        os.close(fd)
        return None


def main() -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    lock_path = os.environ.get("CRON_LOCK_PATH", "/tmp/rainyun-cron.lock")
    fd = _acquire_lock(lock_path)
    if fd is None:
        logger.info("已有任务在执行中，跳过本次调度")
        return 0

    try:
        store = DataStore()
        runner = MultiAccountRunner(store)
        results = runner.run()
        total = len(results)
        success = sum(1 for item in results if item.success)
        logger.info("定时任务完成：%s/%s 成功", success, total)
        return 0
    except Exception as exc:
        logger.exception("定时任务执行失败: %s", exc)
        return 1
    finally:
        if isinstance(fd, int) and fd >= 0:
            os.close(fd)


if __name__ == "__main__":
    sys.exit(main())
