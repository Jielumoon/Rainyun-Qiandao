"""系统设置路由。"""

import logging
import os
from typing import Mapping

from fastapi import APIRouter, Body, Depends

from rainyun.data.models import Settings
from rainyun.data.store import DataStore
from rainyun.notify import send
from rainyun.notify.registry import DEFAULT_REGISTRY
from rainyun.scheduler.cron import normalize_schedule, write_cron_file
from rainyun.web.deps import get_store, require_auth
from rainyun.web.errors import ApiError
from rainyun.web.responses import success_response

router = APIRouter(prefix="/api/system", tags=["system"], dependencies=[Depends(require_auth)])
logger = logging.getLogger(__name__)


@router.get("/settings")
def get_settings(store: DataStore = Depends(get_store)) -> dict:
    data = store.load()
    return success_response(data.settings.to_dict())


@router.put("/settings")
def update_settings(
    payload: dict = Body(default_factory=dict), store: DataStore = Depends(get_store)
) -> dict:
    data = store.load()
    existing_settings = data.settings.to_dict()
    # 保留鉴权配置，避免前端未传 auth 时重置 token 密钥
    existing_auth = dict(existing_settings.get("auth", {}))
    payload_auth = payload.get("auth")
    if isinstance(payload_auth, dict):
        merged_auth = dict(existing_auth)
        merged_auth.update(payload_auth)
        if isinstance(payload_auth.get("token"), dict):
            merged_token = dict(merged_auth.get("token", {}))
            merged_token.update(payload_auth.get("token") or {})
            merged_auth["token"] = merged_token
        elif "token" not in payload_auth:
            merged_auth["token"] = merged_auth.get("token", {})
        else:
            merged_auth["token"] = existing_auth.get("token", {})
        payload["auth"] = merged_auth
    else:
        payload["auth"] = existing_auth
    merged_payload = dict(existing_settings)
    merged_payload.update(payload)
    settings = Settings.from_dict(merged_payload)
    settings.cron_schedule = normalize_schedule(settings.cron_schedule)
    store.update_settings(settings)
    if os.environ.get("CRON_MODE", "false").strip().lower() == "true":
        try:
            write_cron_file(settings.cron_schedule)
        except Exception as exc:
            logger.warning("写入 cron 文件失败: %s", exc)
    return success_response(settings.to_dict())


@router.post("/notify/test")
def test_notify(payload: dict = Body(default_factory=dict), store: DataStore = Depends(get_store)) -> dict:
    channel_id = payload.get("channel_id")
    if not channel_id:
        raise ApiError("缺少通知渠道 ID", status_code=400)
    data = store.load()
    channels = getattr(data.settings, "notify_channels", [])
    channel = next(
        (item for item in channels if isinstance(item, Mapping) and item.get("id") == channel_id),
        None,
    )
    if not channel:
        raise ApiError("通知渠道不存在", status_code=404)
    raw_config = channel.get("config")
    if not isinstance(raw_config, Mapping):
        raw_config = {}
    config = {k: v for k, v in raw_config.items() if isinstance(k, str)}
    if not config:
        raise ApiError("通知配置为空", status_code=400)
    notifiers = DEFAULT_REGISTRY.resolve(config)
    if not notifiers:
        raise ApiError("通知配置无效，未命中任何渠道", status_code=400)
    content = "这是一条测试通知"
    send("雨云通知测试", content, ignore_default_config=True, **config)
    return success_response({"sent": True, "channels": [n.name for n in notifiers]})
