"""系统设置路由。"""

import logging
import os

from fastapi import APIRouter, Body, Depends

from rainyun.data.models import Settings
from rainyun.data.store import DataStore
from rainyun.scheduler.cron import normalize_schedule, write_cron_file
from rainyun.web.deps import get_store, require_auth
from rainyun.web.responses import success_response

router = APIRouter(prefix="/api/system", tags=["system"], dependencies=[Depends(require_auth)])
logger = logging.getLogger(__name__)


@router.get("/settings")
def get_settings(store: DataStore = Depends(get_store)) -> dict:
    data = store.load() if store.data is None else store.data
    return success_response(data.settings.to_dict())


@router.put("/settings")
def update_settings(
    payload: dict = Body(default_factory=dict), store: DataStore = Depends(get_store)
) -> dict:
    data = store.load() if store.data is None else store.data
    settings = Settings.from_dict(payload)
    settings.cron_schedule = normalize_schedule(settings.cron_schedule)
    store.update_settings(settings)
    if os.environ.get("CRON_MODE", "false").strip().lower() == "true":
        try:
            write_cron_file(settings.cron_schedule)
        except Exception as exc:
            logger.warning("写入 cron 文件失败: %s", exc)
    return success_response(settings.to_dict())
