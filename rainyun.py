import io
import json
import logging
import os
import random
import re
import time

import cv2
import ddddocr
import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

COOKIE_FILE = "cookies.json"
# 积分兑换人民币比例 (2000积分 = 1元)
POINTS_TO_CNY_RATE = 2000

# 自定义异常：验证码处理过程中可重试的错误
class CaptchaRetryableError(Exception):
    """可重试的验证码处理错误（如下载失败、网络问题等）"""
    pass

try:
    from notify import send

    print("✅ 通知模块加载成功")
except Exception as e:
    print(f"⚠️ 通知模块加载失败：{e}")

    def send(title, content):
        pass

# 服务器管理模块（可选功能，需要配置 API_KEY）
ServerManager = None
_server_manager_error = None
try:
    from server_manager import ServerManager

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

def save_cookies(driver: WebDriver):
    """保存 cookies 到文件"""
    cookies = driver.get_cookies()
    with open(COOKIE_FILE, "w") as f:
        json.dump(cookies, f)
    logger.info(f"Cookies 已保存到 {COOKIE_FILE}")


def load_cookies(driver: WebDriver) -> bool:
    """从文件加载 cookies"""
    if not os.path.exists(COOKIE_FILE):
        logger.info("未找到 cookies 文件")
        return False
    try:
        with open(COOKIE_FILE, "r") as f:
            cookies = json.load(f)
        # 先访问域名以便设置 cookie
        driver.get("https://app.rainyun.com")
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
    except Exception as e:
        logger.error(f"加载 cookies 失败: {e}")
        return False


def check_login_status(driver: WebDriver, wait: WebDriverWait) -> bool:
    """检查是否已登录"""
    driver.get("https://app.rainyun.com/dashboard")
    time.sleep(3)
    # 如果跳转到登录页面，说明 cookie 失效
    if "login" in driver.current_url:
        logger.info("Cookie 已失效，需要重新登录")
        return False
    # 检查是否成功加载 dashboard
    if driver.current_url == "https://app.rainyun.com/dashboard":
        logger.info("Cookie 有效，已登录")
        return True
    return False


def do_login(driver: WebDriver, wait: WebDriverWait, user: str, pwd: str) -> bool:
    """执行登录流程"""
    logger.info("发起登录请求")
    driver.get("https://app.rainyun.com/auth/login")
    try:
        username = wait.until(EC.visibility_of_element_located((By.NAME, 'login-field')))
        password = wait.until(EC.visibility_of_element_located((By.NAME, 'login-password')))
        login_button = wait.until(EC.visibility_of_element_located((By.XPATH,
                                                                    '//*[@id="app"]/div[1]/div[1]/div/div[2]/fade/div/div/span/form/button')))
        username.send_keys(user)
        password.send_keys(pwd)
        login_button.click()
    except TimeoutException:
        logger.error("页面加载超时，请尝试延长超时时间或切换到国内网络环境！")
        return False
    try:
        login_captcha = wait.until(EC.visibility_of_element_located((By.ID, 'tcaptcha_iframe_dy')))
        logger.warning("触发验证码！")
        driver.switch_to.frame("tcaptcha_iframe_dy")
        if not process_captcha():
            logger.error("登录验证码识别失败")
            return False
    except TimeoutException:
        logger.info("未触发验证码")
    time.sleep(2)  # 给页面一点点缓冲时间
    driver.switch_to.default_content()
    try:
        # 使用显式等待检测登录是否成功（通过判断 URL 变化）
        wait.until(EC.url_contains("dashboard"))
        logger.info("登录成功！")
        save_cookies(driver)
        return True
    except TimeoutException:
        logger.error(f"登录超时或失败！当前 URL: {driver.current_url}")
        return False


def init_selenium() -> WebDriver:
    ops = Options()
    ops.add_argument("--no-sandbox")
    if debug:
        ops.add_experimental_option("detach", True)
    if linux:
        ops.add_argument("--headless")
        ops.add_argument("--disable-gpu")
        ops.add_argument("--disable-dev-shm-usage")
        # 设置 Chromium 二进制路径（支持 ARM 和 AMD64）
        chrome_bin = os.environ.get("CHROME_BIN")
        if chrome_bin and os.path.exists(chrome_bin):
            ops.binary_location = chrome_bin
        # 容器环境使用系统 chromedriver
        chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
        if os.path.exists(chromedriver_path):
            return webdriver.Chrome(service=Service(chromedriver_path), options=ops)
        return webdriver.Chrome(service=Service("./chromedriver"), options=ops)
    return webdriver.Chrome(service=Service("chromedriver.exe"), options=ops)


def download_image(url, filename):
    os.makedirs("temp", exist_ok=True)
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            path = os.path.join("temp", filename)
            with open(path, "wb") as f:
                f.write(response.content)
            return True
        else:
            logger.error(f"下载图片失败！状态码: {response.status_code}, URL: {url}")
            return False
    except requests.RequestException as e:
        logger.error(f"下载图片失败 (网络错误): {url}, 异常: {e}")
        return False


def get_url_from_style(style):
    # 修复：添加空值保护
    if not style:
        raise ValueError("style 属性为空，无法解析 URL")
    match = re.search(r'url\([\"\'\\ ]?(.*?)[\"\'\\ ]?\)', style)
    if not match:
        raise ValueError(f"无法从 style 中解析 URL: {style}")
    return match.group(1)


def get_width_from_style(style):
    # 修复：添加空值保护
    if not style:
        raise ValueError("style 属性为空，无法解析宽度")
    match = re.search(r'width:\s*([\d.]+)px', style)
    if not match:
        raise ValueError(f"无法从 style 中解析宽度: {style}")
    return match.group(1)


def get_height_from_style(style):
    # 修复：添加空值保护
    if not style:
        raise ValueError("style 属性为空，无法解析高度")
    match = re.search(r'height:\s*([\d.]+)px', style)
    if not match:
        raise ValueError(f"无法从 style 中解析高度: {style}")
    return match.group(1)


def process_captcha(retry_count=0):
    if retry_count >= 5:
        logger.error("验证码重试次数过多，任务失败")
        return False
    try:
        download_captcha_img()
        if check_captcha():
            logger.info(f"开始识别验证码 (第 {retry_count + 1} 次尝试)")
            captcha = cv2.imread("temp/captcha.jpg")
            # 修复：检查图片是否成功读取
            if captcha is None:
                logger.error("验证码背景图读取失败，可能下载不完整")
                raise CaptchaRetryableError("验证码图片读取失败")
            with open("temp/captcha.jpg", 'rb') as f:
                captcha_b = f.read()
            bboxes = det.detection(captcha_b)
            result = dict()
            for i in range(len(bboxes)):
                x1, y1, x2, y2 = bboxes[i]
                spec = captcha[y1:y2, x1:x2]
                cv2.imwrite(f"temp/spec_{i + 1}.jpg", spec)
                for j in range(3):
                    similarity, matched = compute_similarity(f"temp/sprite_{j + 1}.jpg", f"temp/spec_{i + 1}.jpg")
                    similarity_key = f"sprite_{j + 1}.similarity"
                    position_key = f"sprite_{j + 1}.position"
                    if similarity_key in result.keys():
                        if float(result[similarity_key]) < similarity:
                            result[similarity_key] = similarity
                            result[position_key] = f"{int((x1 + x2) / 2)},{int((y1 + y2) / 2)}"
                    else:
                        result[similarity_key] = similarity
                        result[position_key] = f"{int((x1 + x2) / 2)},{int((y1 + y2) / 2)}"
            if check_answer(result):
                for i in range(3):
                    similarity_key = f"sprite_{i + 1}.similarity"
                    position_key = f"sprite_{i + 1}.position"
                    positon = result[position_key]
                    logger.info(f"图案 {i + 1} 位于 ({positon})，匹配率：{result[similarity_key]}")
                    slideBg = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="slideBg"]')))
                    style = slideBg.get_attribute("style")
                    x, y = int(positon.split(",")[0]), int(positon.split(",")[1])
                    width_raw, height_raw = captcha.shape[1], captcha.shape[0]
                    width, height = float(get_width_from_style(style)), float(get_height_from_style(style))
                    x_offset, y_offset = float(-width / 2), float(-height / 2)
                    final_x, final_y = int(x_offset + x / width_raw * width), int(y_offset + y / height_raw * height)
                    ActionChains(driver).move_to_element_with_offset(slideBg, final_x, final_y).click().perform()
                confirm = wait.until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="tcStatus"]/div[2]/div[2]/div/div')))
                logger.info("提交验证码")
                confirm.click()
                time.sleep(5)
                result_el = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="tcOperation"]')))
                if 'show-success' in result_el.get_attribute("class"):
                    logger.info("验证码通过")
                    return True
                else:
                    logger.error("验证码未通过，正在重试")
            else:
                logger.error("验证码识别失败，正在重试")
        else:
            logger.error("当前验证码识别率低，尝试刷新")

        reload_btn = driver.find_element(By.XPATH, '//*[@id="reload"]')
        time.sleep(2)
        reload_btn.click()
        time.sleep(2)
        return process_captcha(retry_count + 1)
    except (TimeoutException, ValueError, CaptchaRetryableError) as e:
        # 修复：仅捕获预期异常（超时、解析失败、下载失败），其他程序错误直接抛出便于排查
        logger.error(f"验证码处理异常: {type(e).__name__} - {e}")
        # 尝试刷新验证码重试
        try:
            reload_btn = driver.find_element(By.XPATH, '//*[@id="reload"]')
            time.sleep(2)
            reload_btn.click()
            time.sleep(2)
            return process_captcha(retry_count + 1)
        except Exception as refresh_error:
            logger.error(f"无法刷新验证码，放弃重试: {refresh_error}")
            return False


def download_captcha_img():
    if os.path.exists("temp"):
        for filename in os.listdir("temp"):
            file_path = os.path.join("temp", filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.remove(file_path)
    slideBg = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="slideBg"]')))
    img1_style = slideBg.get_attribute("style")
    img1_url = get_url_from_style(img1_style)
    logger.info("开始下载验证码图片(1): " + img1_url)
    # 修复：检查下载是否成功
    if not download_image(img1_url, "captcha.jpg"):
        raise CaptchaRetryableError("验证码背景图下载失败")
    sprite = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="instruction"]/div/img')))
    img2_url = sprite.get_attribute("src")
    logger.info("开始下载验证码图片(2): " + img2_url)
    # 修复：检查下载是否成功
    if not download_image(img2_url, "sprite.jpg"):
        raise CaptchaRetryableError("验证码小图下载失败")


def check_captcha() -> bool:
    raw = cv2.imread("temp/sprite.jpg")
    # 修复：检查图片是否成功读取
    if raw is None:
        logger.error("验证码小图读取失败，可能下载不完整")
        return False
    for i in range(3):
        w = raw.shape[1]
        temp = raw[:, w // 3 * i: w // 3 * (i + 1)]
        cv2.imwrite(f"temp/sprite_{i + 1}.jpg", temp)
        with open(f"temp/sprite_{i + 1}.jpg", mode="rb") as f:
            temp_rb = f.read()
        if ocr.classification(temp_rb) in ["0", "1"]:
            return False
    return True


# 检查是否存在重复坐标,快速判断识别错误
def check_answer(d: dict) -> bool:
    # 修复：空字典或不完整结果直接返回 False
    # 需要 3 个 sprite 的 similarity + position = 6 个键
    if not d or len(d) < 6:
        logger.warning(f"验证码识别结果不完整，当前仅有 {len(d)} 个键，预期至少 6 个")
        return False
    flipped = dict()
    for key in d.keys():
        flipped[d[key]] = key
    return len(d.values()) == len(flipped.keys())


def compute_similarity(img1_path, img2_path):
    img1 = cv2.imread(img1_path, cv2.IMREAD_GRAYSCALE)
    img2 = cv2.imread(img2_path, cv2.IMREAD_GRAYSCALE)

    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(img1, None)
    kp2, des2 = sift.detectAndCompute(img2, None)

    if des1 is None or des2 is None:
        return 0.0, 0

    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)

    good = [m for m_n in matches if len(m_n) == 2 for m, n in [m_n] if m.distance < 0.8 * n.distance]

    if len(good) == 0:
        return 0.0, 0

    similarity = len(good) / len(matches)
    return similarity, len(good)


def run():
    # 声明全局变量以供其他函数使用
    global driver, wait, ocr, det, debug, linux

    try:
        # 从环境变量读取配置
        timeout = int(os.environ.get("TIMEOUT", "15"))
        max_delay = int(os.environ.get("MAX_DELAY", "90"))
        user = os.environ.get("RAINYUN_USER", "")
        pwd = os.environ.get("RAINYUN_PWD", "")
        debug = os.environ.get("DEBUG", "false").lower() == "true"
        # 容器环境默认启用 Linux 模式
        linux = os.environ.get("LINUX_MODE", "true").lower() == "true"

        # 检查必要配置
        if not user or not pwd:
            logger.error("请设置 RAINYUN_USER 和 RAINYUN_PWD 环境变量")
            return

        # 检查环境模式 (Linux/Windows)
        linux = os.environ.get("LINUX_MODE", "true").lower() == "true"
        debug = os.environ.get("DEBUG", "false").lower() == "true"

        ver = "2.4"
        logger.info(f"━━━━━━ 雨云签到 v{ver} ━━━━━━")

        delay = random.randint(0, max_delay)
        delay_sec = random.randint(0, 60)
        if not debug:
            logger.info(f"随机延时等待 {delay} 分钟 {delay_sec} 秒")
            time.sleep(delay * 60 + delay_sec)
        logger.info("初始化 ddddocr")
        ocr = ddddocr.DdddOcr(ocr=True, show_ad=False)
        det = ddddocr.DdddOcr(det=True, show_ad=False)
        logger.info("初始化 Selenium")
        driver = init_selenium()
        # 过 Selenium 检测
        with open("stealth.min.js", mode="r") as f:
            js = f.read()
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": js
        })
        wait = WebDriverWait(driver, timeout)

        # 尝试使用 cookie 登录
        logged_in = False
        if load_cookies(driver):
            logged_in = check_login_status(driver, wait)

        # cookie 无效则进行正常登录
        if not logged_in:
            logged_in = do_login(driver, wait, user, pwd)

        if not logged_in:
            logger.error("登录失败，任务终止")
            return

        logger.info("正在转到赚取积分页")
        driver.get("https://app.rainyun.com/account/reward/earn")

        # 检查签到状态：先找"领取奖励"按钮，找不到就检查是否已签到
        try:
            # 使用显示等待寻找按钮
            earn = wait.until(EC.presence_of_element_located((By.XPATH,
                                       "//span[contains(text(), '每日签到')]/ancestor::div[1]//a[contains(text(), '领取奖励')]")))
            logger.info("点击赚取积分")
            earn.click()
        except TimeoutException:
            # 检查是否已经签到（按钮可能显示"已领取"、"已完成"等）
            already_signed_patterns = ['已领取', '已完成', '已签到', '明日再来']
            page_source = driver.page_source
            for pattern in already_signed_patterns:
                if pattern in page_source:
                    logger.info(f"今日已签到（检测到：{pattern}），跳过签到流程")
                    # 直接跳到获取积分信息
                    try:
                        points_raw = wait.until(EC.visibility_of_element_located((By.XPATH,
                            '//*[@id="app"]/div[1]/div[3]/div[2]/div/div/div[2]/div[1]/div[1]/div/p/div/h3'))).get_attribute("textContent")
                        current_points = int(''.join(re.findall(r'\d+', points_raw)))
                        logger.info(f"当前剩余积分: {current_points} | 约为 {current_points / POINTS_TO_CNY_RATE:.2f} 元")
                    except Exception:
                        logger.info("无法获取当前积分信息")
                    return
            # 如果既没找到领取按钮，也没检测到已签到，说明页面结构可能变了
            raise Exception("未找到签到按钮，且未检测到已签到状态，可能页面结构已变更")
        logger.info("处理验证码")
        driver.switch_to.frame("tcaptcha_iframe_dy")
        if not process_captcha():
            # 失败时尝试记录当前页面源码的关键部分，方便排查
            logger.error(f"验证码重试次数过多，任务失败。当前页面状态: {driver.current_url}")
            raise Exception("验证码识别重试次数过多，签到失败")
        driver.switch_to.default_content()
        points_raw = wait.until(EC.visibility_of_element_located((By.XPATH,
                                         '//*[@id="app"]/div[1]/div[3]/div[2]/div/div/div[2]/div[1]/div[1]/div/p/div/h3'))).get_attribute(
            "textContent")
        current_points = int(''.join(re.findall(r'\d+', points_raw)))
        logger.info(f"当前剩余积分: {current_points} | 约为 {current_points / POINTS_TO_CNY_RATE:.2f} 元")
        logger.info("任务执行成功！")
    except Exception as e:
        logger.error(f"脚本执行异常终止: {e}")

    finally:
        # === 核心逻辑：无论成功失败，这里都会执行 ===

        # 1. 关闭浏览器
        try:
            driver.quit()
        except:
            pass

        # 2. 服务器到期检查和自动续费（需要配置 API_KEY）
        server_report = ""
        api_key = os.environ.get("RAINYUN_API_KEY", "")
        if api_key and ServerManager:
            logger.info("━━━━━━ 开始检查服务器状态 ━━━━━━")
            try:
                manager = ServerManager(api_key)
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


if __name__ == "__main__":
    run()
