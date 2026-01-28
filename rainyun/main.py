import io
import logging
import os
import random
import re
import shutil
import time
from dataclasses import dataclass
from typing import Protocol, Sequence

import cv2
import ddddocr
import numpy as np
import requests
from .api.client import RainyunAPI
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as EC

from .config import Config, get_default_config
from .browser.cookies import load_cookies
from .browser.locators import XPATH_CONFIG
from .browser.pages import LoginPage, RewardPage
from .browser.session import BrowserSession, RuntimeContext

# 自定义异常：验证码处理过程中可重试的错误
class CaptchaRetryableError(Exception):
    """可重试的验证码处理错误（如下载失败、网络问题等）"""
    pass

try:
    from .notify import configure, send

    print("✅ 通知模块加载成功")
except Exception as e:
    print(f"⚠️ 通知模块加载失败：{e}")

    def configure(_config: Config) -> None:
        pass

    def send(title, content):
        pass

# 服务器管理模块（可选功能，需要配置 API_KEY）
ServerManager = None
_server_manager_error = None
try:
    from .server.manager import ServerManager

    print("✅ 服务器管理模块加载成功")
except Exception as e:
    print(f"⚠️ 服务器管理模块加载失败：{e}")
    _server_manager_error = str(e)
# 创建一个内存缓冲区，用于存储所有日志
log_capture_string = io.StringIO()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# 配置 logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

#输出到字符串 (新增功能)
string_handler = logging.StreamHandler(log_capture_string)
string_handler.setFormatter(formatter)
logger.addHandler(string_handler)


@dataclass(frozen=True)
class MatchResult:
    positions: list[tuple[int, int]]
    similarities: list[float]
    method: str


class CaptchaMatcher(Protocol):
    name: str

    def match(
        self,
        background: np.ndarray,
        sprites: list[np.ndarray],
        bboxes: list[tuple[int, int, int, int]],
    ) -> MatchResult | None:
        ...


class CaptchaSolver(Protocol):
    def solve(
        self,
        background: np.ndarray,
        sprites: list[np.ndarray],
        bboxes: list[tuple[int, int, int, int]],
    ) -> MatchResult | None:
        ...


class StrategyCaptchaSolver:
    def __init__(self, matchers: Sequence[CaptchaMatcher]) -> None:
        self.matchers = list(matchers)

    def solve(
        self,
        background: np.ndarray,
        sprites: list[np.ndarray],
        bboxes: list[tuple[int, int, int, int]],
    ) -> MatchResult | None:
        for matcher in self.matchers:
            result = matcher.match(background, sprites, bboxes)
            if result:
                logger.info(f"验证码匹配策略命中: {matcher.name}")
                return result
            logger.warning(f"验证码匹配策略失败: {matcher.name}")
        return None


class SiftMatcher:
    name = "sift"

    def __init__(self) -> None:
        self._sift = cv2.SIFT_create() if hasattr(cv2, "SIFT_create") else None
        if not self._sift:
            logger.warning("SIFT 不可用，将跳过 SiftMatcher")

    def match(
        self,
        background: np.ndarray,
        sprites: list[np.ndarray],
        bboxes: list[tuple[int, int, int, int]],
    ) -> MatchResult | None:
        if not self._sift:
            return None
        return build_match_result(
            background,
            sprites,
            bboxes,
            lambda sprite, spec: compute_sift_similarity(sprite, spec, self._sift),
            self.name,
        )


class TemplateMatcher:
    name = "template"

    def match(
        self,
        background: np.ndarray,
        sprites: list[np.ndarray],
        bboxes: list[tuple[int, int, int, int]],
    ) -> MatchResult | None:
        return build_match_result(
            background,
            sprites,
            bboxes,
            compute_template_similarity,
            self.name,
        )


def temp_path(ctx: RuntimeContext, filename: str) -> str:
    return os.path.join(ctx.temp_dir, filename)


def clear_temp_dir(temp_dir: str) -> None:
    if not os.path.exists(temp_dir):
        return
    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        if os.path.isfile(file_path) or os.path.islink(file_path):
            os.remove(file_path)


def download_image(url: str, output_path: str, config: Config) -> bool:
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    last_error = None
    for attempt in range(1, config.download_max_retries + 1):
        try:
            response = requests.get(url, timeout=config.download_timeout)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True
            last_error = f"status_code={response.status_code}"
            logger.warning(f"下载图片失败 (第 {attempt} 次): {last_error}, URL: {url}")
        except requests.RequestException as e:
            last_error = str(e)
            logger.warning(f"下载图片失败 (第 {attempt} 次): {e}, URL: {url}")
        if attempt < config.download_max_retries:
            time.sleep(config.download_retry_delay)
    logger.error(f"下载图片失败，已重试 {config.download_max_retries} 次: {last_error}, URL: {url}")
    return False


def download_image_bytes(url: str, config: Config, fallback_path: str | None = None) -> bytes:
    last_error = None
    for attempt in range(1, config.download_max_retries + 1):
        try:
            response = requests.get(url, timeout=config.download_timeout)
            if response.status_code == 200 and response.content:
                return response.content
            last_error = f"status_code={response.status_code}"
            logger.warning(f"内存下载图片失败 (第 {attempt} 次): {last_error}, URL: {url}")
        except requests.RequestException as e:
            last_error = str(e)
            logger.warning(f"内存下载图片失败 (第 {attempt} 次): {e}, URL: {url}")
        if attempt < config.download_max_retries:
            time.sleep(config.download_retry_delay)
    if fallback_path:
        logger.warning("内存下载失败，尝试降级为文件下载")
        if download_image(url, fallback_path, config):
            with open(fallback_path, "rb") as f:
                return f.read()
    raise CaptchaRetryableError(f"验证码图片下载失败: {last_error}")


def get_url_from_style(style):
    # 修复：添加空值保护
    if not style:
        raise ValueError("style 属性为空，无法解析 URL")
    match = re.search(r"url\(([^)]+)\)", style, re.IGNORECASE)
    if not match:
        raise ValueError(f"无法从 style 中解析 URL: {style}")
    url = match.group(1).strip().strip('"').strip("'")
    return url


def get_width_from_style(style):
    # 修复：添加空值保护
    if not style:
        raise ValueError("style 属性为空，无法解析宽度")
    match = re.search(r"width\s*:\s*([\d.]+)px", style, re.IGNORECASE)
    if not match:
        raise ValueError(f"无法从 style 中解析宽度: {style}")
    return float(match.group(1))


def get_height_from_style(style):
    # 修复：添加空值保护
    if not style:
        raise ValueError("style 属性为空，无法解析高度")
    match = re.search(r"height\s*:\s*([\d.]+)px", style, re.IGNORECASE)
    if not match:
        raise ValueError(f"无法从 style 中解析高度: {style}")
    return float(match.group(1))


def get_element_size(element) -> tuple[float, float]:
    size = element.size or {}
    width = size.get("width", 0)
    height = size.get("height", 0)
    if not width or not height:
        raise ValueError("无法从元素尺寸解析宽高")
    return float(width), float(height)


def decode_image_bytes(image_bytes: bytes, label: str) -> np.ndarray:
    if not image_bytes:
        raise CaptchaRetryableError(f"{label} 数据为空，无法解码")
    buffer = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise CaptchaRetryableError(f"{label} 解码失败")
    return image


def encode_image_bytes(image: np.ndarray, label: str) -> bytes:
    if image is None or image.size == 0:
        raise CaptchaRetryableError(f"{label} 为空，无法编码")
    success, encoded = cv2.imencode(".jpg", image)
    if not success:
        raise CaptchaRetryableError(f"{label} 编码失败")
    return encoded.tobytes()


def split_sprite_image(sprite: np.ndarray) -> list[np.ndarray]:
    if sprite is None or sprite.size == 0:
        raise CaptchaRetryableError("验证码小图为空，无法切分")
    width = sprite.shape[1]
    if width < 3:
        raise CaptchaRetryableError("验证码小图宽度异常，无法切分")
    step = width // 3
    if step == 0:
        raise CaptchaRetryableError("验证码小图切分宽度为 0")
    return [
        sprite[:, 0:step],
        sprite[:, step:step * 2],
        sprite[:, step * 2:width],
    ]


def detect_captcha_bboxes(
    ctx: RuntimeContext,
    captcha_bytes: bytes,
    captcha_image: np.ndarray,
) -> list[tuple[int, int, int, int]]:
    payloads = [
        ("raw", captcha_bytes),
        ("reencode", encode_image_bytes(captcha_image, "验证码背景图")),
    ]
    for label, payload in payloads:
        try:
            bboxes = ctx.det.detection(payload)
            if bboxes:
                logger.info(f"验证码检测成功({label}): {len(bboxes)} 个候选框")
                return bboxes
            logger.warning(f"验证码检测结果为空({label})")
        except Exception as e:
            logger.warning(f"验证码检测失败({label}): {e}")
    return []


def normalize_gray(image: np.ndarray) -> np.ndarray:
    if image is None:
        return image
    if len(image.shape) == 2:
        return image
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def compute_sift_similarity(sprite: np.ndarray, spec: np.ndarray, sift) -> float:
    sprite_gray = normalize_gray(sprite)
    spec_gray = normalize_gray(spec)
    kp1, des1 = sift.detectAndCompute(sprite_gray, None)
    kp2, des2 = sift.detectAndCompute(spec_gray, None)
    if des1 is None or des2 is None:
        return 0.0
    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)
    good = [m for m_n in matches if len(m_n) == 2 for m, n in [m_n] if m.distance < 0.8 * n.distance]
    if not matches or len(good) == 0:
        return 0.0
    return len(good) / len(matches)


def compute_template_similarity(sprite: np.ndarray, spec: np.ndarray) -> float:
    sprite_gray = normalize_gray(sprite)
    spec_gray = normalize_gray(spec)
    if sprite_gray is None or spec_gray is None or sprite_gray.size == 0 or spec_gray.size == 0:
        return 0.0
    if sprite_gray.shape != spec_gray.shape:
        sprite_gray = cv2.resize(sprite_gray, (spec_gray.shape[1], spec_gray.shape[0]))
    result = cv2.matchTemplate(spec_gray, sprite_gray, cv2.TM_CCOEFF_NORMED)
    return float(np.max(result))


def build_match_result(
    background: np.ndarray,
    sprites: list[np.ndarray],
    bboxes: list[tuple[int, int, int, int]],
    similarity_fn,
    method: str,
) -> MatchResult | None:
    if not bboxes:
        logger.warning("验证码检测结果为空，无法匹配")
        return None
    if len(sprites) != 3:
        logger.warning(f"验证码小图数量异常: {len(sprites)}")
        return None
    best_positions: list[tuple[int, int] | None] = [None, None, None]
    best_scores: list[float | None] = [None, None, None]
    for bbox in bboxes:
        if len(bbox) != 4:
            continue
        x1, y1, x2, y2 = map(int, bbox)
        if x2 <= x1 or y2 <= y1:
            continue
        spec = background[y1:y2, x1:x2]
        if spec.size == 0:
            continue
        center = (int((x1 + x2) / 2), int((y1 + y2) / 2))
        for index, sprite in enumerate(sprites):
            if sprite is None or sprite.size == 0:
                continue
            similarity = similarity_fn(sprite, spec)
            if best_scores[index] is None or similarity > best_scores[index]:
                best_scores[index] = similarity
                best_positions[index] = center
    if any(pos is None for pos in best_positions):
        return None
    return MatchResult(
        positions=[pos for pos in best_positions if pos is not None],
        similarities=[float(score) if score is not None else 0.0 for score in best_scores],
        method=method,
    )


def log_match_result(result: MatchResult) -> None:
    for index, (position, similarity) in enumerate(zip(result.positions, result.similarities), start=1):
        x, y = position
        logger.info(f"图案 {index} 位于 ({x},{y})，匹配率：{similarity:.4f}，策略：{result.method}")


def process_captcha(ctx: RuntimeContext, retry_count: int = 0):
    """
    处理验证码逻辑（循环实现，避免递归栈溢出）
    - 整体重试上限由配置项 captcha_retry_limit 控制
    - 启用 captcha_retry_unlimited 后无限重试直到成功
    - 内部图片下载重试由配置项 download_max_retries 控制
    """
    def refresh_captcha() -> bool:
        try:
            reload_btn = ctx.driver.find_element(*XPATH_CONFIG["CAPTCHA_RELOAD"])
            time.sleep(2)
            reload_btn.click()
            time.sleep(2)
            return True
        except Exception as refresh_error:
            logger.error(f"无法刷新验证码，放弃重试: {refresh_error}")
            return False

    solver = StrategyCaptchaSolver([SiftMatcher(), TemplateMatcher()])
    current_retry = retry_count
    while True:
        if not ctx.config.captcha_retry_unlimited and current_retry >= ctx.config.captcha_retry_limit:
            logger.error("验证码重试次数过多，任务失败")
            return False
        if ctx.config.captcha_retry_unlimited and current_retry > 0:
            logger.info(f"无限重试模式，当前第 {current_retry + 1} 次尝试")

        try:
            captcha_bytes, captcha_image, sprites = download_captcha_assets(ctx)
            if check_captcha(ctx, sprites):
                logger.info(f"开始识别验证码 (第 {current_retry + 1} 次尝试)")
                bboxes = detect_captcha_bboxes(ctx, captcha_bytes, captcha_image)
                if not bboxes:
                    logger.error("验证码检测失败，正在重试")
                else:
                    result = solver.solve(captcha_image, sprites, bboxes)
                    if result:
                        log_match_result(result)
                        if check_answer(result):
                            for position in result.positions:
                                slide_bg = ctx.wait.until(
                                    EC.visibility_of_element_located(XPATH_CONFIG["CAPTCHA_BG"])
                                )
                                style = slide_bg.get_attribute("style")
                                x, y = position
                                width_raw, height_raw = captcha_image.shape[1], captcha_image.shape[0]
                                try:
                                    width = get_width_from_style(style)
                                    height = get_height_from_style(style)
                                except ValueError:
                                    width, height = get_element_size(slide_bg)
                                x_offset, y_offset = float(-width / 2), float(-height / 2)
                                final_x = int(x_offset + x / width_raw * width)
                                final_y = int(y_offset + y / height_raw * height)
                                ActionChains(ctx.driver).move_to_element_with_offset(
                                    slide_bg, final_x, final_y
                                ).click().perform()
                            confirm = ctx.wait.until(EC.element_to_be_clickable(XPATH_CONFIG["CAPTCHA_SUBMIT"]))
                            logger.info("提交验证码")
                            confirm.click()
                            time.sleep(5)
                            result_el = ctx.wait.until(EC.visibility_of_element_located(XPATH_CONFIG["CAPTCHA_OP"]))
                            if 'show-success' in result_el.get_attribute("class"):
                                logger.info("验证码通过")
                                return True
                            logger.error("验证码未通过，正在重试")
                        else:
                            logger.error("验证码识别结果无效，正在重试")
                    else:
                        logger.error("验证码匹配失败，正在重试")
            else:
                logger.error("当前验证码识别率低，尝试刷新")

            if not refresh_captcha():
                return False
            current_retry += 1
        except (TimeoutException, ValueError, CaptchaRetryableError) as e:
            logger.error(f"验证码处理异常: {type(e).__name__} - {e}")
            if not refresh_captcha():
                return False
            current_retry += 1


def download_captcha_assets(ctx: RuntimeContext) -> tuple[bytes, np.ndarray, list[np.ndarray]]:
    clear_temp_dir(ctx.temp_dir)
    slide_bg = ctx.wait.until(EC.visibility_of_element_located(XPATH_CONFIG["CAPTCHA_BG"]))
    img1_style = slide_bg.get_attribute("style")
    img1_url = get_url_from_style(img1_style)
    logger.info("开始下载验证码图片(1): " + img1_url)
    captcha_bytes = download_image_bytes(img1_url, ctx.config, temp_path(ctx, "captcha.jpg"))
    sprite = ctx.wait.until(EC.visibility_of_element_located(XPATH_CONFIG["CAPTCHA_IMG_INSTRUCTION"]))
    img2_url = sprite.get_attribute("src")
    logger.info("开始下载验证码图片(2): " + img2_url)
    sprite_bytes = download_image_bytes(img2_url, ctx.config, temp_path(ctx, "sprite.jpg"))
    captcha_image = decode_image_bytes(captcha_bytes, "验证码背景图")
    sprite_image = decode_image_bytes(sprite_bytes, "验证码小图")
    sprites = split_sprite_image(sprite_image)
    return captcha_bytes, captcha_image, sprites


def check_captcha(ctx: RuntimeContext, sprites: list[np.ndarray]) -> bool:
    if len(sprites) != 3:
        logger.error(f"验证码小图数量异常，期望 3，实际 {len(sprites)}")
        return False
    for index, sprite in enumerate(sprites, start=1):
        sprite_bytes = encode_image_bytes(sprite, f"验证码小图{index}")
        if ctx.ocr.classification(sprite_bytes) in ["0", "1"]:
            logger.warning(f"验证码小图 {index} 识别为低置信度标记，跳过本次识别")
            return False
    return True


# 检查是否存在重复坐标,快速判断识别错误
def check_answer(result: MatchResult) -> bool:
    if not result.positions or len(result.positions) < 3:
        logger.warning(f"验证码识别坐标不足，当前仅有 {len(result.positions) if result.positions else 0} 个")
        return False
    if len(result.similarities) < 3:
        logger.warning(f"验证码匹配率不足，当前仅有 {len(result.similarities)} 个")
        return False
    if len(result.positions) != len(set(result.positions)):
        logger.warning(f"验证码识别坐标重复: {result.positions}")
        return False
    return True


def run():
    ctx = None
    driver = None
    temp_dir = None
    debug = False
    config = None
    session = None
    try:
        config = Config.from_env()
        configure(config)
        timeout = config.timeout
        max_delay = config.max_delay
        user = config.rainyun_user
        pwd = config.rainyun_pwd
        debug = config.debug
        # 容器环境默认启用 Linux 模式
        linux = config.linux_mode

        # 检查必要配置
        if not user or not pwd:
            logger.error("请设置 RAINYUN_USER 和 RAINYUN_PWD 环境变量")
            return

        api_key = config.rainyun_api_key
        api_client = RainyunAPI(api_key, config=config)

        logger.info(f"━━━━━━ 雨云签到 v{config.app_version} ━━━━━━")
        if config.captcha_retry_unlimited:
            logger.warning("已启用无限重试模式，验证码将持续重试直到成功或手动停止")

        # 初始积分记录
        start_points = 0
        if api_key:
            try:
                start_points = api_client.get_user_points()
                logger.info(f"签到前初始积分: {start_points}")
            except Exception as e:
                logger.warning(f"获取初始积分失败: {e}")

        delay = random.randint(0, max_delay)
        delay_sec = random.randint(0, 60)
        if not debug:
            logger.info(f"随机延时等待 {delay} 分钟 {delay_sec} 秒")
            time.sleep(delay * 60 + delay_sec)
        logger.info("初始化 ddddocr")
        ocr = ddddocr.DdddOcr(ocr=True, show_ad=False)
        det = ddddocr.DdddOcr(det=True, show_ad=False)
        logger.info("初始化 Selenium")
        session = BrowserSession(config=config, debug=debug, linux=linux)
        driver, wait, temp_dir = session.start()
        ctx = RuntimeContext(
            driver=driver,
            wait=wait,
            ocr=ocr,
            det=det,
            temp_dir=temp_dir,
            api=api_client,
            config=config
        )

        login_page = LoginPage(ctx, captcha_handler=process_captcha)
        reward_page = RewardPage(ctx, captcha_handler=process_captcha)

        # 尝试使用 cookie 登录
        logged_in = False
        if load_cookies(ctx.driver, ctx.config):
            logged_in = login_page.check_login_status()

        # cookie 无效则进行正常登录
        if not logged_in:
            logged_in = login_page.login(user, pwd)

        if not logged_in:
            logger.error("登录失败，任务终止")
            return

        reward_page.handle_daily_reward(start_points)
        
        logger.info("任务执行成功！")
    except Exception as e:
        logger.error(f"脚本执行异常终止: {e}")

    finally:
        # === 核心逻辑：无论成功失败，这里都会执行 ===

        # 1. 关闭浏览器
        if session:
            session.close()

        # 2. 服务器到期检查和自动续费（需要配置 API_KEY）
        server_report = ""
        final_config = config or get_default_config()
        api_key = final_config.rainyun_api_key
        if api_key and ServerManager:
            logger.info("━━━━━━ 开始检查服务器状态 ━━━━━━")
            try:
                manager = ServerManager(api_key, config=final_config)
                result = manager.check_and_renew()
                server_report = "\n\n" + manager.generate_report(result)
                logger.info("服务器检查完成")
            except Exception as e:
                logger.error(f"服务器检查失败: {e}")
                server_report = f"\n\n⚠️ 服务器检查失败: {e}"
        elif api_key and not ServerManager:
            # 修复：配置了 API_KEY 但模块加载失败时明确告警
            logger.error(f"已配置 RAINYUN_API_KEY 但服务器管理模块加载失败: {_server_manager_error}")
            server_report = f"\n\n⚠️ 服务器管理模块加载失败: {_server_manager_error}"
        elif not api_key:
            logger.info("未配置 RAINYUN_API_KEY，跳过服务器管理功能")

        # 3. 获取所有日志内容
        log_content = log_capture_string.getvalue()

        # 4. 发送通知（签到日志 + 服务器状态，一次性推送）
        logger.info("正在发送通知...")
        send("雨云签到", log_content + server_report)

        # 5. 释放内存
        log_capture_string.close()
        if temp_dir and not debug:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    run()
