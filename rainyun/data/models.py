"""数据模型与默认配置结构。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

DEFAULT_DATA_VERSION = 1
DEFAULT_TOKEN_EXPIRES_DAYS = 7
DEFAULT_DATA_PATH = "data/config.json"


def _as_mapping(data: Any) -> Mapping[str, Any]:
    return data if isinstance(data, Mapping) else {}


def _read_str(data: Mapping[str, Any], key: str, default: str = "") -> str:
    value = data.get(key)
    return value if isinstance(value, str) else default


def _read_bool(data: Mapping[str, Any], key: str, default: bool = False) -> bool:
    value = data.get(key)
    if isinstance(value, bool):
        return value
    return default


def _read_int(data: Mapping[str, Any], key: str, default: int = 0) -> int:
    value = data.get(key)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return default


def _read_float(data: Mapping[str, Any], key: str, default: float = 0.0) -> float:
    value = data.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        try:
            return float(stripped)
        except ValueError:
            return default
    return default


def _read_list_int(data: Mapping[str, Any], key: str) -> list[int]:
    value = data.get(key)
    if not isinstance(value, list):
        return []
    result: list[int] = []
    for item in value:
        if isinstance(item, int):
            result.append(item)
        elif isinstance(item, str):
            stripped = item.strip()
            if stripped.isdigit():
                result.append(int(stripped))
    return result


def _read_dict_str(data: Mapping[str, Any], key: str) -> dict[str, str]:
    value = data.get(key)
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, str] = {}
    for k, v in value.items():
        if isinstance(k, str) and isinstance(v, str):
            result[k] = v
    return result


@dataclass
class TokenConfig:
    """Token 配置。"""

    secret: str = ""
    expires_in_days: int = DEFAULT_TOKEN_EXPIRES_DAYS

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "TokenConfig":
        payload = _as_mapping(data)
        return cls(
            secret=_read_str(payload, "secret", ""),
            expires_in_days=_read_int(payload, "expires_in_days", DEFAULT_TOKEN_EXPIRES_DAYS),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "secret": self.secret,
            "expires_in_days": self.expires_in_days,
        }


@dataclass
class AuthConfig:
    """轻量鉴权配置。"""

    enabled: bool = True
    password_hash: str = ""
    token: TokenConfig = field(default_factory=TokenConfig)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "AuthConfig":
        payload = _as_mapping(data)
        return cls(
            enabled=_read_bool(payload, "enabled", True),
            password_hash=_read_str(payload, "password_hash", ""),
            token=TokenConfig.from_dict(payload.get("token")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "password_hash": self.password_hash,
            "token": self.token.to_dict(),
        }


@dataclass
class Account:
    """账户配置。"""

    id: str = ""
    name: str = ""
    username: str = ""
    password: str = ""
    api_key: str = ""
    enabled: bool = True
    renew_products: list[int] = field(default_factory=list)
    last_checkin: str = ""
    last_status: str = "unknown"
    created_at: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "Account":
        payload = _as_mapping(data)
        return cls(
            id=_read_str(payload, "id", ""),
            name=_read_str(payload, "name", ""),
            username=_read_str(payload, "username", ""),
            password=_read_str(payload, "password", ""),
            api_key=_read_str(payload, "api_key", ""),
            enabled=_read_bool(payload, "enabled", True),
            renew_products=_read_list_int(payload, "renew_products"),
            last_checkin=_read_str(payload, "last_checkin", ""),
            last_status=_read_str(payload, "last_status", "unknown"),
            created_at=_read_str(payload, "created_at", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "username": self.username,
            "password": self.password,
            "api_key": self.api_key,
            "enabled": self.enabled,
            "renew_products": list(self.renew_products),
            "last_checkin": self.last_checkin,
            "last_status": self.last_status,
            "created_at": self.created_at,
        }


@dataclass
class Settings:
    """全局设置。"""

    auto_renew: bool = True
    renew_threshold_days: int = 7
    cron_schedule: str = "0 8 * * *"
    timeout: int = 15
    max_delay: int = 90
    debug: bool = False
    request_timeout: int = 15
    max_retries: int = 3
    retry_delay: float = 2.0
    download_timeout: int = 10
    download_max_retries: int = 3
    download_retry_delay: float = 2.0
    captcha_retry_limit: int = 5
    captcha_retry_unlimited: bool = False
    captcha_save_samples: bool = False
    skip_push_title: str = ""
    notify_config: dict[str, str] = field(default_factory=dict)
    auth: AuthConfig = field(default_factory=AuthConfig)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "Settings":
        payload = _as_mapping(data)
        return cls(
            auto_renew=_read_bool(payload, "auto_renew", True),
            renew_threshold_days=_read_int(payload, "renew_threshold_days", 7),
            cron_schedule=_read_str(payload, "cron_schedule", "0 8 * * *"),
            timeout=_read_int(payload, "timeout", 15),
            max_delay=_read_int(payload, "max_delay", 90),
            debug=_read_bool(payload, "debug", False),
            request_timeout=_read_int(payload, "request_timeout", 15),
            max_retries=_read_int(payload, "max_retries", 3),
            retry_delay=_read_float(payload, "retry_delay", 2.0),
            download_timeout=_read_int(payload, "download_timeout", 10),
            download_max_retries=_read_int(payload, "download_max_retries", 3),
            download_retry_delay=_read_float(payload, "download_retry_delay", 2.0),
            captcha_retry_limit=_read_int(payload, "captcha_retry_limit", 5),
            captcha_retry_unlimited=_read_bool(payload, "captcha_retry_unlimited", False),
            captcha_save_samples=_read_bool(payload, "captcha_save_samples", False),
            skip_push_title=_read_str(payload, "skip_push_title", ""),
            notify_config=_read_dict_str(payload, "notify_config"),
            auth=AuthConfig.from_dict(payload.get("auth")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "auto_renew": self.auto_renew,
            "renew_threshold_days": self.renew_threshold_days,
            "cron_schedule": self.cron_schedule,
            "timeout": self.timeout,
            "max_delay": self.max_delay,
            "debug": self.debug,
            "request_timeout": self.request_timeout,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "download_timeout": self.download_timeout,
            "download_max_retries": self.download_max_retries,
            "download_retry_delay": self.download_retry_delay,
            "captcha_retry_limit": self.captcha_retry_limit,
            "captcha_retry_unlimited": self.captcha_retry_unlimited,
            "captcha_save_samples": self.captcha_save_samples,
            "skip_push_title": self.skip_push_title,
            "notify_config": dict(self.notify_config),
            "auth": self.auth.to_dict(),
        }


@dataclass
class ConfigData:
    """数据文件配置结构。"""

    version: int = DEFAULT_DATA_VERSION
    accounts: list[Account] = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> "ConfigData":
        payload = _as_mapping(data)
        accounts_data = payload.get("accounts")
        accounts: list[Account] = []
        if isinstance(accounts_data, list):
            for item in accounts_data:
                if isinstance(item, Mapping):
                    accounts.append(Account.from_dict(item))
        return cls(
            version=_read_int(payload, "version", DEFAULT_DATA_VERSION),
            accounts=accounts,
            settings=Settings.from_dict(payload.get("settings")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "accounts": [account.to_dict() for account in self.accounts],
            "settings": self.settings.to_dict(),
        }


def build_default_config() -> dict[str, Any]:
    """生成默认空配置。"""

    return ConfigData().to_dict()


def write_default_config(path: str | Path) -> dict[str, Any]:
    """写入默认空配置（不做原子写入，留给 DataStore 处理）。"""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = build_default_config()
    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return data
