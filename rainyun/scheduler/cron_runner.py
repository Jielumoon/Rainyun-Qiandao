"""定时任务入口（基于 DataStore）。"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime

from rainyun.config import Config
from rainyun.data.store import DataStore
from rainyun.web.logs import ensure_file_handler
from rainyun.scheduler.runner import MultiAccountRunner

logger = logging.getLogger(__name__)

try:
    from rainyun.notify import configure, send
except Exception as exc:  # pragma: no cover - optional dependency

    def configure(_config: Config) -> None:
        logger.warning("通知模块不可用: %s", exc)

    def send(_title: str, _content: str, **_kwargs) -> None:
        logger.warning("通知模块不可用，跳过发送")


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
    ensure_file_handler()
    lock_path = os.environ.get("CRON_LOCK_PATH", "/tmp/rainyun-cron.lock")
    fd = _acquire_lock(lock_path)
    if fd is None:
        logger.info("已有任务在执行中，跳过本次调度")
        return 0

    try:
        store = DataStore()
        runner = MultiAccountRunner(store)
        results = runner.run(delay=True)
        total = len(results)
        success = sum(1 for item in results if item.success)
        renew_results = runner.run_renew()
        renew_total = len(renew_results)
        renew_success = sum(1 for item in renew_results if item.success)
        renew_checked = sum(1 for item in renew_results if item.has_api_key)
        renew_skipped = sum(1 for item in renew_results if not item.has_api_key)
        logger.info("定时签到完成：%s/%s 成功", success, total)
        if renew_results:
            logger.info(
                "定时续费检查完成：成功 %s/%s，跳过 %s",
                renew_success,
                renew_checked,
                renew_skipped,
            )
        logger.info(
            "定时任务完成：签到 %s/%s，续费检查 %s/%s",
            success,
            total,
            renew_success,
            renew_checked,
        )
        try:
            data = store.load()
            account = next((item for item in data.accounts if item.enabled), None)
            if account:
                config = Config.from_account(account, data.settings)
                configure(config)
                content_lines = [f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
                if results:
                    checkin_names = [
                        f"{index}.{item.account_name or item.account_id}"
                        for index, item in enumerate(results, start=1)
                    ]
                    content_lines.append("签到账户: " + "  ".join(checkin_names))
                    content_lines.append("签到结果:")
                    for item in results:
                        name = item.account_name or item.account_id
                        if item.current_points is not None:
                            points_text = f"当前积分 {item.current_points}"
                            if item.earned_points is not None:
                                points_text += f" (本次 {item.earned_points:+d} 分)"
                        else:
                            points_text = "当前积分未知"
                        if item.success:
                            status = (
                                "🟡 已签到"
                                if item.status == "already_signed"
                                else "✅ 成功"
                            )
                            content_lines.append(f"{name} {status} {points_text}")
                        else:
                            reason = item.message or "失败"
                            content_lines.append(
                                f"{name} ❌ 失败 {points_text}  原因: {reason}"
                            )
                content_lines.append("")
                if renew_results:
                    content_lines.append("续费账户:")
                    for index, item in enumerate(renew_results, start=1):
                        name = item.account_name or item.account_id
                        if not item.has_api_key:
                            content_lines.append(f"{index}.{name} - 无apikey - 跳过续费")
                            continue
                        whitelist_flag = "白名单" if item.whitelist_ids else "无白名单"
                        whitelist_ids = (
                            ",".join(str(x) for x in item.whitelist_ids)
                            if item.whitelist_ids
                            else "-"
                        )
                        server_names = "、".join(item.server_names) if item.server_names else "无服务器"
                        content_lines.append(
                            f"{index}.{name} - {whitelist_flag} - {whitelist_ids} - {server_names}"
                        )
                content_lines.append("")
                content_lines.append("续费详细")
                for item in renew_results:
                    name = item.account_name or item.account_id
                    content_lines.append(f"【{name}】")
                    if not item.has_api_key:
                        content_lines.append("无apikey - 跳过续费")
                    elif item.report:
                        content_lines.append(item.report)
                    else:
                        content_lines.append(f"结果: {item.message}")
                    content_lines.append("")
                content = "\n".join(content_lines).strip()
                failed = total - success
                if total == 0:
                    title = "雨云定时任务"
                elif failed == 0:
                    title = f"雨云定时任务（签到全部成功，共 {total} 个账户）"
                else:
                    title = f"雨云定时任务（签到 {success} 成功 {failed} 失败）"
                send(title, content)
            else:
                logger.info("未启用任何账户，跳过通知")
        except Exception as notify_exc:
            logger.error("发送定时通知失败: %s", notify_exc)
        return 0
    except Exception as exc:
        logger.exception("定时任务执行失败: %s", exc)
        return 1
    finally:
        if isinstance(fd, int) and fd >= 0:
            os.close(fd)


if __name__ == "__main__":
    sys.exit(main())
