"""多账户串行调度执行。"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

import ddddocr

from rainyun.api.client import RainyunAPI
from rainyun.browser.cookies import load_cookies
from rainyun.browser.pages import LoginPage, RewardPage
from rainyun.browser.session import BrowserSession, RuntimeContext
from rainyun.config import Config
from rainyun.data.store import DataStore
from rainyun.main import process_captcha

logger = logging.getLogger(__name__)

try:
    from rainyun.notify import configure
except Exception:

    def configure(_config: Config) -> None:
        pass


@dataclass
class AccountRunResult:
    account_id: str
    success: bool
    message: str = ""


class MultiAccountRunner:
    """串行执行启用账户并回写结果。"""

    def __init__(self, store: DataStore) -> None:
        self.store = store

    def run(self) -> list[AccountRunResult]:
        data = self.store.load() if self.store.data is None else self.store.data
        if not data.accounts:
            logger.info("未配置任何账户，跳过多账户调度")
            return []

        base_config = Config.from_env(os.environ)
        settings = data.settings
        base_config = replace(
            base_config,
            timeout=getattr(settings, "timeout", base_config.timeout),
            max_delay=getattr(settings, "max_delay", base_config.max_delay),
            debug=getattr(settings, "debug", base_config.debug),
            request_timeout=getattr(settings, "request_timeout", base_config.request_timeout),
            max_retries=getattr(settings, "max_retries", base_config.max_retries),
            retry_delay=getattr(settings, "retry_delay", base_config.retry_delay),
            download_timeout=getattr(settings, "download_timeout", base_config.download_timeout),
            download_max_retries=getattr(settings, "download_max_retries", base_config.download_max_retries),
            download_retry_delay=getattr(settings, "download_retry_delay", base_config.download_retry_delay),
            captcha_retry_limit=getattr(settings, "captcha_retry_limit", base_config.captcha_retry_limit),
            captcha_retry_unlimited=getattr(
                settings, "captcha_retry_unlimited", base_config.captcha_retry_unlimited
            ),
            captcha_save_samples=getattr(settings, "captcha_save_samples", base_config.captcha_save_samples),
        )
        session = BrowserSession(base_config, debug=base_config.debug, linux=base_config.linux_mode)
        driver, wait, temp_dir = session.start()
        ocr = ddddocr.DdddOcr(ocr=True, show_ad=False)
        det = ddddocr.DdddOcr(det=True, show_ad=False)

        results: list[AccountRunResult] = []
        try:
            for account in data.accounts:
                if not account.enabled:
                    continue
                results.append(
                    self._run_single_account(
                        account=account,
                        settings=data.settings,
                        driver=driver,
                        wait=wait,
                        ocr=ocr,
                        det=det,
                        temp_dir=temp_dir,
                    )
                )
        finally:
            session.close()
            if temp_dir and not base_config.debug:
                shutil.rmtree(temp_dir, ignore_errors=True)
        return results

    def _run_single_account(
        self,
        account: Any,
        settings: Any,
        driver,
        wait,
        ocr: ddddocr.DdddOcr,
        det: ddddocr.DdddOcr,
        temp_dir: str,
    ) -> AccountRunResult:
        config = Config.from_account(account, settings)
        configure(config)
        api_client = RainyunAPI(config.rainyun_api_key, config=config)
        ctx = RuntimeContext(
            driver=driver,
            wait=wait,
            ocr=ocr,
            det=det,
            temp_dir=temp_dir,
            api=api_client,
            config=config,
        )

        try:
            driver.delete_all_cookies()
        except Exception as exc:
            logger.warning("清理 cookies 失败: %s", exc)

        try:
            start_points = 0
            if config.rainyun_api_key:
                try:
                    start_points = api_client.get_user_points()
                except Exception as exc:
                    logger.warning("获取初始积分失败: %s", exc)

            login_page = LoginPage(ctx, captcha_handler=process_captcha)
            reward_page = RewardPage(ctx, captcha_handler=process_captcha)

            logged_in = False
            if load_cookies(ctx.driver, ctx.config):
                logged_in = login_page.check_login_status()
            if not logged_in:
                logged_in = login_page.login(config.rainyun_user, config.rainyun_pwd)
            if not logged_in:
                return self._mark_result(account, success=False, message="login_failed")

            reward_page.handle_daily_reward(start_points)
            return self._mark_result(account, success=True, message="success")
        except Exception as exc:
            logger.error("账户 %s 执行失败: %s", getattr(account, "id", "unknown"), exc)
            return self._mark_result(account, success=False, message=str(exc))

    def _mark_result(self, account: Any, success: bool, message: str) -> AccountRunResult:
        now = datetime.now().isoformat()
        account.last_checkin = now
        account.last_status = "success" if success else message or "failed"
        try:
            self.store.update_account(account)
        except Exception as exc:
            logger.error("回写账户状态失败: %s", exc)
        return AccountRunResult(account_id=getattr(account, "id", ""), success=success, message=message)
