"""通知入口与发送编排。"""

import logging
import re
import threading

from rainyun.notify.channels import _as_bool, one
from rainyun.notify.registry import DEFAULT_REGISTRY
from rainyun.notify.state import apply_overrides, configure, ensure_loaded, get_skip_title, push_config

logger = logging.getLogger(__name__)


def send(title: str, content: str, ignore_default_config: bool = False, **kwargs) -> None:
    ensure_loaded()
    apply_overrides(kwargs, ignore_default_config)

    if not content:
        logger.warning(f"{title} 推送内容为空！")
        return

    skip_title = get_skip_title()
    if skip_title and title in re.split("\n", skip_title):
        logger.info(f"{title} 在SKIP_PUSH_TITLE环境变量内，跳过推送！")
        return

    if _as_bool(push_config.get("HITOKOTO"), default=True):
        content += "\n\n" + one()

    notifiers = DEFAULT_REGISTRY.resolve(push_config)
    if not notifiers:
        logger.warning("无有效推送渠道，请检查通知变量是否正确")
        return

    def safe_run(notifier) -> None:
        try:
            notifier.send(title, content)
        except Exception as e:
            logger.error(f"{notifier.name} 线程执行崩溃: {e}")

    threads = [
        threading.Thread(target=safe_run, args=(notifier,), name=notifier.name)
        for notifier in notifiers
    ]
    [thread.start() for thread in threads]
    [thread.join() for thread in threads]


__all__ = ["configure", "send"]
