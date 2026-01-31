"""浏览器会话封装。"""

import logging
import os
import tempfile
from dataclasses import dataclass

import ddddocr
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support.wait import WebDriverWait

from rainyun.api.client import RainyunAPI
from rainyun.config import Config

logger = logging.getLogger(__name__)


@dataclass
class RuntimeContext:
    driver: WebDriver
    wait: WebDriverWait
    ocr: ddddocr.DdddOcr
    det: ddddocr.DdddOcr
    temp_dir: str
    api: RainyunAPI
    config: Config


class BrowserSession:
    def __init__(self, config: Config, debug: bool, linux: bool) -> None:
        self.config = config
        self.debug = debug
        self.linux = linux
        self.driver = None
        self.wait = None
        self.temp_dir = None

    def start(self) -> tuple[WebDriver, WebDriverWait, str]:
        driver = self._init_selenium()
        self._apply_stealth(driver)
        wait = WebDriverWait(driver, self.config.timeout)
        temp_dir = tempfile.mkdtemp(prefix="rainyun-")
        self.driver = driver
        self.wait = wait
        self.temp_dir = temp_dir
        return driver, wait, temp_dir

    def close(self) -> None:
        if not self.driver:
            return
        try:
            self.driver.quit()
        except Exception:
            pass

    def _init_selenium(self) -> WebDriver:
        ops = Options()
        ops.add_argument("--no-sandbox")
        if self.debug:
            ops.add_experimental_option("detach", True)
        if self.linux:
            ops.add_argument("--headless")
            ops.add_argument("--disable-gpu")
            ops.add_argument("--disable-dev-shm-usage")
            # 低配模式：适用于 1核1G 小鸡
            if self.config.chrome_low_memory:
                logger.info("启用 Chrome 低内存模式")
                # 注意：--single-process 在 Docker 容器中容易导致崩溃，不使用
                ops.add_argument("--disable-extensions")
                ops.add_argument("--disable-background-networking")
                ops.add_argument("--disable-sync")
                ops.add_argument("--disable-translate")
                ops.add_argument("--disable-default-apps")
                ops.add_argument("--no-first-run")
                ops.add_argument("--disable-software-rasterizer")
                ops.add_argument("--js-flags=--max-old-space-size=256")
            # 设置 Chromium 二进制路径（支持 ARM 和 AMD64）
            if self.config.chrome_bin and os.path.exists(self.config.chrome_bin):
                ops.binary_location = self.config.chrome_bin
            # 容器环境使用系统 chromedriver
            driver_path = self.config.chromedriver_path
            if not os.path.exists(driver_path):
                candidates = [
                    "/usr/bin/chromedriver",
                    "/usr/local/bin/chromedriver",
                    "/usr/lib/chromium/chromedriver",
                    "/usr/lib/chromium-browser/chromedriver",
                ]
                for candidate in candidates:
                    if os.path.exists(candidate):
                        driver_path = candidate
                        break
            if os.path.exists(driver_path):
                return webdriver.Chrome(service=Service(driver_path), options=ops)
            return webdriver.Chrome(service=Service("./chromedriver"), options=ops)
        return webdriver.Chrome(service=Service("chromedriver.exe"), options=ops)

    def _apply_stealth(self, driver: WebDriver) -> None:
        with open("stealth.min.js", mode="r") as f:
            js = f.read()
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": js})
