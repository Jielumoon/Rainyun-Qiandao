"""Cookies 读写。"""

import json
import logging
import os
import time

from selenium.webdriver.chrome.webdriver import WebDriver

from rainyun.config import Config
from rainyun.browser.urls import build_app_url

logger = logging.getLogger(__name__)


def save_cookies(driver: WebDriver, config: Config) -> None:
    """保存 cookies 到文件。"""
    cookies = driver.get_cookies()
    cookie_dir = os.path.dirname(config.cookie_file)
    if cookie_dir:
        os.makedirs(cookie_dir, exist_ok=True)
    with open(config.cookie_file, "w") as f:
        json.dump(cookies, f)
    logger.info(f"Cookies 已保存到 {config.cookie_file}")


def load_cookies(driver: WebDriver, config: Config) -> bool:
    """从文件加载 cookies。"""
    if not os.path.exists(config.cookie_file):
        logger.info("未找到 cookies 文件")
        return False
    try:
        with open(config.cookie_file, "r") as f:
            cookies = json.load(f)
        # 先访问域名以便设置 cookie
        driver.get(build_app_url(config, "/"))
        for cookie in cookies:
            # 移除可能导致问题的字段
            cookie.pop("sameSite", None)
            cookie.pop("expiry", None)
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(f"添加 cookie 失败: {e}")
        logger.info("Cookies 已加载")
        return True
    except json.JSONDecodeError as e:
        backup_path = f"{config.cookie_file}.bad-{time.strftime('%Y%m%d-%H%M%S')}"
        try:
            os.replace(config.cookie_file, backup_path)
            logger.warning(f"Cookies 文件损坏，已备份到 {backup_path}")
        except OSError as rename_error:
            logger.warning(f"备份 cookies 文件失败: {rename_error}")
        try:
            with open(config.cookie_file, "w") as f:
                json.dump([], f)
            logger.info("Cookies 文件已清空")
        except OSError as write_error:
            logger.warning(f"清空 cookies 文件失败: {write_error}")
        logger.error(f"加载 cookies 失败: {e}")
        return False
    except Exception as e:
        logger.error(f"加载 cookies 失败: {e}")
        return False
