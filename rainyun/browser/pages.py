"""页面对象封装。"""

import logging
import re
import time
from typing import Callable

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from rainyun.browser.cookies import save_cookies
from rainyun.browser.locators import XPATH_CONFIG
from rainyun.browser.session import RuntimeContext
from rainyun.browser.urls import build_app_url

logger = logging.getLogger(__name__)
CaptchaHandler = Callable[[RuntimeContext], bool]


class LoginPage:
    def __init__(self, ctx: RuntimeContext, captcha_handler: CaptchaHandler) -> None:
        self.ctx = ctx
        self.captcha_handler = captcha_handler

    def check_login_status(self) -> bool:
        """检查是否已登录。"""
        user_label = self.ctx.config.display_name or self.ctx.config.rainyun_user
        self.ctx.driver.get(build_app_url(self.ctx.config, "/dashboard"))
        time.sleep(3)
        # 如果跳转到登录页面，说明 cookie 失效
        if "login" in self.ctx.driver.current_url:
            logger.info(f"用户 {user_label} Cookie 已失效，需要重新登录")
            return False
        # 检查是否成功加载 dashboard
        if self.ctx.driver.current_url == build_app_url(self.ctx.config, "/dashboard"):
            logger.info(f"用户 {user_label} Cookie 有效，已登录")
            return True
        return False

    def login(self, user: str, pwd: str) -> bool:
        """执行登录流程。"""
        user_label = self.ctx.config.display_name or user
        logger.info(f"用户 {user_label} 发起登录请求")
        self.ctx.driver.get(build_app_url(self.ctx.config, "/auth/login"))
        try:
            username = self.ctx.wait.until(EC.visibility_of_element_located((By.NAME, "login-field")))
            password = self.ctx.wait.until(EC.visibility_of_element_located((By.NAME, "login-password")))
            # 优化：使用文本和类型定位登录按钮，增强稳定性
            login_button = self.ctx.wait.until(
                EC.visibility_of_element_located((By.XPATH, XPATH_CONFIG["LOGIN_BTN"]))
            )
            username.send_keys(user)
            password.send_keys(pwd)
            login_button.click()
        except TimeoutException:
            logger.error(f"用户 {user_label} 页面加载超时，请尝试延长超时时间或切换到国内网络环境！")
            return False
        try:
            self.ctx.wait.until(EC.visibility_of_element_located((By.ID, "tcaptcha_iframe_dy")))
            logger.warning(f"用户 {user_label} 触发验证码！")
            self.ctx.driver.switch_to.frame("tcaptcha_iframe_dy")
            if not self.captcha_handler(self.ctx):
                logger.error(f"用户 {user_label} 登录验证码识别失败")
                return False
        except TimeoutException:
            logger.info(f"用户 {user_label} 未触发验证码")
        time.sleep(2)  # 给页面一点点缓冲时间
        self.ctx.driver.switch_to.default_content()
        try:
            # 使用显式等待检测登录是否成功（通过判断 URL 变化）
            self.ctx.wait.until(EC.url_contains("dashboard"))
            logger.info(f"用户 {user_label} 登录成功！")
            save_cookies(self.ctx.driver, self.ctx.config)
            return True
        except TimeoutException:
            logger.error(f"用户 {user_label} 登录超时或失败！当前 URL: {self.ctx.driver.current_url}")
            return False


class RewardPage:
    _DAILY_SIGN_CLAIM_TEXT = "领取奖励"
    # 只在“每日签到”模块内匹配这些文案，避免“已完成”在其他任务卡片出现导致误判
    _DAILY_SIGN_DONE_PATTERNS = ("已完成", "已领取", "已签到", "明日再来")
    _DAILY_SIGN_DONE_WAIT_SECONDS = 10

    def __init__(self, ctx: RuntimeContext, captcha_handler: CaptchaHandler) -> None:
        self.ctx = ctx
        self.captcha_handler = captcha_handler

    def open(self) -> None:
        self.ctx.driver.get(build_app_url(self.ctx.config, "/account/reward/earn"))

    def _get_daily_sign_header_text(self) -> str:
        """读取“每日签到”卡片头部可见文本。

        注意：必须限定在每日签到模块范围内匹配，避免全页扫文案导致误判。
        """

        try:
            elements = self.ctx.driver.find_elements(By.XPATH, XPATH_CONFIG["SIGN_IN_HEADER"])
            if not elements:
                return ""
            header = elements[0]
            return (header.get_attribute("innerText") or header.text or "").strip()
        except Exception:
            return ""

    def _detect_daily_sign_done_pattern(self) -> str | None:
        header_text = self._get_daily_sign_header_text()
        for pattern in self._DAILY_SIGN_DONE_PATTERNS:
            if pattern in header_text:
                return pattern
        return None

    def _wait_daily_sign_done_pattern(self, timeout: int | None = None) -> str | None:
        if timeout is None:
            timeout = self._DAILY_SIGN_DONE_WAIT_SECONDS
        wait = WebDriverWait(self.ctx.driver, timeout, poll_frequency=0.5)
        try:
            return wait.until(lambda driver: self._detect_daily_sign_done_pattern() or False)
        except TimeoutException:
            return None

    def handle_daily_reward(self, start_points: int) -> dict:
        user_label = self.ctx.config.display_name or self.ctx.config.rainyun_user
        self.open()
        try:
            # 先确保“每日签到”模块已加载，再做任何状态判定/点击操作
            self.ctx.wait.until(EC.presence_of_element_located((By.XPATH, XPATH_CONFIG["SIGN_IN_HEADER"])))
        except TimeoutException:
            raise Exception("奖励页加载超时：未找到每日签到模块，可能页面结构已变更")

        done_pattern = self._detect_daily_sign_done_pattern()
        if done_pattern:
            logger.info(
                f":down_arrow: 用户 {user_label} 今日已签到（每日签到模块检测到：{done_pattern}），跳过签到流程"
            )
            current_points, earned = self._log_points(start_points)
            return {
                "status": "already_signed",
                "current_points": current_points,
                "earned": earned,
            }

        try:
            # 使用显式等待寻找按钮（只针对“每日签到”模块内的领取按钮）
            earn = self.ctx.wait.until(EC.presence_of_element_located((By.XPATH, XPATH_CONFIG["SIGN_IN_BTN"])))
            logger.info(f"用户 {user_label} 点击领取奖励")
            earn.click()
        except TimeoutException:
            header_text = self._get_daily_sign_header_text()
            if self._DAILY_SIGN_CLAIM_TEXT in header_text:
                raise Exception("未找到每日签到的领取按钮（模块仍显示“领取奖励”），可能页面结构已变更")
            raise Exception("未找到每日签到的领取按钮，且未检测到完成状态，可能页面结构已变更")

        logger.info(f"用户 {user_label} 处理验证码")
        try:
            self.ctx.wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "tcaptcha_iframe_dy")))
            if not self.captcha_handler(self.ctx):
                logger.error(
                    f"用户 {user_label} 验证码重试次数过多，签到失败。当前页面状态: {self.ctx.driver.current_url}"
                )
                raise Exception("验证码识别重试次数过多，签到失败")
        except TimeoutException:
            # 极少数情况下可能不触发验证码：直接走状态判定，避免无意义失败
            logger.info(f"用户 {user_label} 未触发验证码")
        finally:
            self.ctx.driver.switch_to.default_content()

        done_pattern = self._wait_daily_sign_done_pattern()
        if not done_pattern:
            header_text = self._get_daily_sign_header_text()
            if self._DAILY_SIGN_CLAIM_TEXT in header_text:
                raise Exception("验证码处理结束后每日签到仍显示“领取奖励”，未检测到“已完成”，签到可能失败")
            raise Exception("验证码处理结束后未检测到每日签到完成状态，可能页面结构已变更")

        current_points, earned = self._log_points(start_points)
        logger.info(f"用户 {user_label} 签到成功（每日签到模块检测到：{done_pattern}）")
        return {
            "status": "signed",
            "current_points": current_points,
            "earned": earned,
        }

    def _log_points(self, start_points: int) -> tuple[int | None, int | None]:
        user_label = self.ctx.config.display_name or self.ctx.config.rainyun_user
        try:
            current_points = self.ctx.api.get_user_points()
            earned = current_points - start_points
            logger.info(
                f"用户 {user_label} 当前剩余积分: {current_points} (本次获得 {earned} 分) | 约为 {current_points / self.ctx.config.points_to_cny_rate:.2f} 元"
            )
            return current_points, earned
        except Exception:
            logger.info(f"用户 {user_label} 无法通过 API 获取当前积分信息")
            return None, None
