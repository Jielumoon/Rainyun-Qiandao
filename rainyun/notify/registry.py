"""通知通道注册表。"""

from dataclasses import dataclass
from typing import Callable, Iterable

from rainyun.notify.channels import (
    _as_bool,
    aibotk,
    bark,
    chat,
    chronocat,
    console,
    custom_notify,
    dingding_bot,
    feishu_bot,
    go_cqhttp,
    gotify,
    iGot,
    ntfy,
    pushdeer,
    pushme,
    pushplus_bot,
    qmsg_bot,
    serverJ,
    smtp,
    telegram_bot,
    wecom_app,
    wecom_bot,
    weplus_bot,
    wxpusher_bot,
)


@dataclass(frozen=True)
class FunctionNotifier:
    name: str
    enabled: Callable[[dict], bool]
    handler: Callable[[str, str], None]

    def is_enabled(self, config: dict) -> bool:
        return self.enabled(config)

    def send(self, title: str, content: str) -> None:
        self.handler(title, content)


class NotifierRegistry:
    def __init__(self) -> None:
        self._items: list[FunctionNotifier] = []

    def register(self, notifier: FunctionNotifier) -> None:
        self._items.append(notifier)

    def resolve(self, config: dict) -> list[FunctionNotifier]:
        return [notifier for notifier in self._items if notifier.is_enabled(config)]

    def all(self) -> Iterable[FunctionNotifier]:
        return list(self._items)


def build_default_registry() -> NotifierRegistry:
    registry = NotifierRegistry()
    registry.register(FunctionNotifier("bark", lambda cfg: bool(cfg.get("BARK_PUSH")), bark))
    registry.register(
        FunctionNotifier("console", lambda cfg: _as_bool(cfg.get("CONSOLE"), default=False), console)
    )
    registry.register(
        FunctionNotifier(
            "dingding_bot",
            lambda cfg: bool(cfg.get("DD_BOT_TOKEN") and cfg.get("DD_BOT_SECRET")),
            dingding_bot,
        )
    )
    registry.register(FunctionNotifier("feishu_bot", lambda cfg: bool(cfg.get("FSKEY")), feishu_bot))
    registry.register(
        FunctionNotifier(
            "go_cqhttp",
            lambda cfg: bool(cfg.get("GOBOT_URL") and cfg.get("GOBOT_QQ")),
            go_cqhttp,
        )
    )
    registry.register(
        FunctionNotifier(
            "gotify",
            lambda cfg: bool(cfg.get("GOTIFY_URL") and cfg.get("GOTIFY_TOKEN")),
            gotify,
        )
    )
    registry.register(FunctionNotifier("igot", lambda cfg: bool(cfg.get("IGOT_PUSH_KEY")), iGot))
    registry.register(FunctionNotifier("serverJ", lambda cfg: bool(cfg.get("PUSH_KEY")), serverJ))
    registry.register(FunctionNotifier("pushdeer", lambda cfg: bool(cfg.get("DEER_KEY")), pushdeer))
    registry.register(
        FunctionNotifier(
            "chat",
            lambda cfg: bool(cfg.get("CHAT_URL") and cfg.get("CHAT_TOKEN")),
            chat,
        )
    )
    registry.register(
        FunctionNotifier(
            "pushplus",
            lambda cfg: bool(cfg.get("PUSH_PLUS_TOKEN")),
            pushplus_bot,
        )
    )
    registry.register(
        FunctionNotifier(
            "weplus_bot",
            lambda cfg: bool(cfg.get("WE_PLUS_BOT_TOKEN")),
            weplus_bot,
        )
    )
    registry.register(
        FunctionNotifier(
            "qmsg_bot",
            lambda cfg: bool(cfg.get("QMSG_KEY") and cfg.get("QMSG_TYPE")),
            qmsg_bot,
        )
    )
    registry.register(FunctionNotifier("wecom_app", lambda cfg: bool(cfg.get("QYWX_AM")), wecom_app))
    registry.register(FunctionNotifier("wecom_bot", lambda cfg: bool(cfg.get("QYWX_KEY")), wecom_bot))
    registry.register(
        FunctionNotifier(
            "telegram_bot",
            lambda cfg: bool(cfg.get("TG_BOT_TOKEN") and cfg.get("TG_USER_ID")),
            telegram_bot,
        )
    )
    registry.register(
        FunctionNotifier(
            "aibotk",
            lambda cfg: bool(
                cfg.get("AIBOTK_KEY") and cfg.get("AIBOTK_TYPE") and cfg.get("AIBOTK_NAME")
            ),
            aibotk,
        )
    )
    registry.register(
        FunctionNotifier(
            "smtp",
            lambda cfg: bool(
                cfg.get("SMTP_SERVER")
                and cfg.get("SMTP_SSL")
                and cfg.get("SMTP_EMAIL")
                and cfg.get("SMTP_PASSWORD")
                and cfg.get("SMTP_NAME")
            ),
            smtp,
        )
    )
    registry.register(FunctionNotifier("pushme", lambda cfg: bool(cfg.get("PUSHME_KEY")), pushme))
    registry.register(
        FunctionNotifier(
            "chronocat",
            lambda cfg: bool(
                cfg.get("CHRONOCAT_URL")
                and cfg.get("CHRONOCAT_QQ")
                and cfg.get("CHRONOCAT_TOKEN")
            ),
            chronocat,
        )
    )
    registry.register(
        FunctionNotifier(
            "custom_notify",
            lambda cfg: bool(cfg.get("WEBHOOK_URL") and cfg.get("WEBHOOK_METHOD")),
            custom_notify,
        )
    )
    registry.register(FunctionNotifier("ntfy", lambda cfg: bool(cfg.get("NTFY_TOPIC")), ntfy))
    registry.register(
        FunctionNotifier(
            "wxpusher_bot",
            lambda cfg: bool(
                cfg.get("WXPUSHER_APP_TOKEN")
                and (cfg.get("WXPUSHER_TOPIC_IDS") or cfg.get("WXPUSHER_UIDS"))
            ),
            wxpusher_bot,
        )
    )
    return registry


DEFAULT_REGISTRY = build_default_registry()
