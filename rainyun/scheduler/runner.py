"""多账户串行调度执行。"""

from __future__ import annotations

import logging
import random
import time
import os
import shutil
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from rainyun.api.client import RainyunAPI
from rainyun.browser.cookies import load_cookies
from rainyun.browser.pages import LoginPage, RewardPage
from rainyun.browser.session import BrowserSession, RuntimeContext
from rainyun.config import Config
from rainyun.data.store import DataStore
from rainyun.server.manager import ServerManager
from rainyun.main import LazyDdddOcr, process_captcha

logger = logging.getLogger(__name__)

try:
    from rainyun.notify import configure
except Exception:

    def configure(_config: Config) -> None:
        pass


@dataclass
class AccountRunResult:
    account_id: str
    account_name: str
    success: bool
    status: str
    current_points: int | None = None
    earned_points: int | None = None
    message: str = ""


@dataclass
class AccountRenewResult:
    account_id: str
    account_name: str
    has_api_key: bool
    whitelist_ids: list[int]
    server_names: list[str]
    success: bool
    message: str = ""
    report: str = ""


class MultiAccountRunner:
    """串行执行启用账户并回写结果。"""

    def __init__(self, store: DataStore) -> None:
        self.store = store

    def _build_base_config(self, settings: Any) -> Config:
        base_config = Config.from_env(os.environ)
        return replace(
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

    def _create_session(self, settings: Any):
        base_config = self._build_base_config(settings)
        session = BrowserSession(base_config, debug=base_config.debug, linux=base_config.linux_mode)
        driver, wait, temp_dir = session.start()
        ocr = LazyDdddOcr(det=False)
        det = LazyDdddOcr(det=True)
        return base_config, session, driver, wait, temp_dir, ocr, det

    def _apply_random_delay(self, settings: Any) -> None:
        debug = getattr(settings, "debug", False)
        max_delay = getattr(settings, "max_delay", 0)
        if debug:
            logger.info("调试模式已开启，跳过随机延时")
            return
        if not isinstance(max_delay, int) or max_delay <= 0:
            return
        delay_min = random.randint(0, max_delay)
        delay_sec = random.randint(0, 60)
        logger.info("随机延时等待 %s 分钟 %s 秒", delay_min, delay_sec)
        time.sleep(delay_min * 60 + delay_sec)

    def _close_session(self, session: BrowserSession, temp_dir: str | None, base_config: Config) -> None:
        session.close()
        if temp_dir and not base_config.debug:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def run(self, delay: bool = False) -> list[AccountRunResult]:
        data = self.store.load() if self.store.data is None else self.store.data
        if not data.accounts:
            logger.info("未配置任何账户，跳过多账户调度")
            return []
        if not any(getattr(account, "enabled", False) for account in data.accounts):
            logger.info("没有启用的账户，跳过多账户调度")
            return []
        if delay:
            self._apply_random_delay(data.settings)

        base_config, session, driver, wait, temp_dir, ocr, det = self._create_session(data.settings)

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
            self._close_session(session, temp_dir, base_config)
        return results

    def run_for_account(self, account_id: str, delay: bool = False) -> AccountRunResult | None:
        data = self.store.load() if self.store.data is None else self.store.data
        account = next(
            (item for item in data.accounts if str(getattr(item, "id", "")) == str(account_id)),
            None,
        )
        if not account:
            return None
        if delay:
            self._apply_random_delay(data.settings)
        base_config, session, driver, wait, temp_dir, ocr, det = self._create_session(data.settings)
        try:
            return self._run_single_account(
                account=account,
                settings=data.settings,
                driver=driver,
                wait=wait,
                ocr=ocr,
                det=det,
                temp_dir=temp_dir,
            )
        finally:
            self._close_session(session, temp_dir, base_config)

    def run_renew(self) -> list[AccountRenewResult]:
        data = self.store.load() if self.store.data is None else self.store.data
        if not data.accounts:
            logger.info("未配置任何账户，跳过续费检查")
            return []
        results: list[AccountRenewResult] = []
        for account in data.accounts:
            if not account.enabled:
                continue
            account_id = str(getattr(account, "id", "") or "").strip()
            account_name = str(getattr(account, "name", "") or "").strip() or account_id
            if not getattr(account, "api_key", ""):
                results.append(
                    AccountRenewResult(
                        account_id=account_id,
                        account_name=account_name,
                        has_api_key=False,
                        whitelist_ids=[],
                        server_names=[],
                        success=False,
                        message="no_api_key",
                    )
                )
                continue
            try:
                config = Config.from_account(account, data.settings)
                manager = ServerManager(account.api_key, config=config)
                result = manager.check_and_renew()
                report = manager.generate_report(result)
                server_names = [
                    item.get("name", "") for item in result.get("servers", []) if item.get("name")
                ]
                whitelist_ids = list(config.renew_product_ids)
                results.append(
                    AccountRenewResult(
                        account_id=account_id,
                        account_name=account_name,
                        has_api_key=True,
                        whitelist_ids=whitelist_ids,
                        server_names=server_names,
                        success=True,
                        message="ok",
                        report=report,
                    )
                )
            except Exception as exc:
                logger.error("账户 %s 续费检查失败: %s", account_id, exc)
                results.append(
                    AccountRenewResult(
                        account_id=account_id,
                        account_name=account_name,
                        has_api_key=True,
                        whitelist_ids=[],
                        server_names=[],
                        success=False,
                        message=str(exc),
                    )
                )
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
                return self._mark_result(
                    account, success=False, message="login_failed", status="failed"
                )

            reward_result = reward_page.handle_daily_reward(start_points)
            return self._mark_result(
                account,
                success=True,
                message="success",
                status=reward_result.get("status", "success"),
                current_points=reward_result.get("current_points"),
                earned_points=reward_result.get("earned"),
            )
        except Exception as exc:
            logger.error("账户 %s 签到失败: %s", getattr(account, "id", "unknown"), exc)
            return self._mark_result(account, success=False, message=str(exc), status="failed")

    def _mark_result(
        self,
        account: Any,
        success: bool,
        message: str,
        status: str,
        current_points: int | None = None,
        earned_points: int | None = None,
    ) -> AccountRunResult:
        now = datetime.now().isoformat()
        account.last_checkin = now
        account.last_status = "success" if success else message or "failed"
        try:
            self.store.update_account(account)
        except Exception as exc:
            logger.error("回写账户状态失败: %s", exc)
        account_id = str(getattr(account, "id", "") or "").strip()
        account_name = str(getattr(account, "name", "") or "").strip() or account_id
        return AccountRunResult(
            account_id=account_id,
            account_name=account_name,
            success=success,
            status=status,
            current_points=current_points,
            earned_points=earned_points,
            message=message,
        )
