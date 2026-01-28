"""通知配置状态管理。"""

from rainyun.config import Config, DEFAULT_PUSH_CONFIG, get_default_config

push_config = DEFAULT_PUSH_CONFIG.copy()
_config_loaded = False
_skip_push_title = ""


def configure(config: Config) -> None:
    global _config_loaded, _skip_push_title
    push_config.clear()
    push_config.update(config.push_config)
    _skip_push_title = config.skip_push_title
    _config_loaded = True


def ensure_loaded() -> None:
    if not _config_loaded:
        configure(get_default_config())


def apply_overrides(overrides: dict, ignore_default_config: bool) -> None:
    if not overrides:
        return
    if ignore_default_config:
        push_config.clear()
        push_config.update(overrides)
    else:
        push_config.update(overrides)


def get_skip_title() -> str:
    return _skip_push_title
