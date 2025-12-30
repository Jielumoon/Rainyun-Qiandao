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
from selenium.common import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

COOKIE_FILE = "cookies.json"


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
        process_captcha()
    except TimeoutException:
        logger.info("未触发验证码")
    time.sleep(5)
    driver.switch_to.default_content()
    if driver.current_url == "https://app.rainyun.com/dashboard":
        logger.info("登录成功！")
        save_cookies(driver)
        return True
    else:
        logger.error("登录失败！")
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
    response = requests.get(url, timeout=10)
    if response.status_code == 200:
        path = os.path.join("temp", filename)
        with open(path, "wb") as f:
            f.write(response.content)
        return True
    else:
        logger.error("下载图片失败！")
        return False


def get_url_from_style(style):
    return re.search(r'url\(["\']?(.*?)["\']?\)', style).group(1)


def get_width_from_style(style):
    return re.search(r'width:\s*([\d.]+)px', style).group(1)


def get_height_from_style(style):
    return re.search(r'height:\s*([\d.]+)px', style).group(1)


def process_captcha():
    try:
        download_captcha_img()
        if check_captcha():
            logger.info("开始识别验证码")
            captcha = cv2.imread("temp/captcha.jpg")
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
                result = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="tcOperation"]')))
                if result.get_attribute("class") == 'tc-opera pointer show-success':
                    logger.info("验证码通过")
                    return
                else:
                    logger.error("验证码未通过，正在重试")
            else:
                logger.error("验证码识别失败，正在重试")
        else:
            logger.error("当前验证码识别率低，尝试刷新")
        reload = driver.find_element(By.XPATH, '//*[@id="reload"]')
        time.sleep(5)
        reload.click()
        time.sleep(5)
        process_captcha()
    except TimeoutException:
        logger.error("获取验证码图片失败")


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
    download_image(img1_url, "captcha.jpg")
    sprite = wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="instruction"]/div/img')))
    img2_url = sprite.get_attribute("src")
    logger.info("开始下载验证码图片(2): " + img2_url)
    download_image(img2_url, "sprite.jpg")


def check_captcha() -> bool:
    raw = cv2.imread("temp/sprite.jpg")
    for i in range(3):
        w = raw.shape[1]
        temp = raw[:, w // 3 * i: w // 3 * (i + 1)]
        cv2.imwrite(f"temp/sprite_{i + 1}.jpg", temp)
        with open(f"temp/sprite_{i + 1}.jpg", mode="rb") as f:
            temp_rb = f.read()
        if ocr.classification(temp_rb) in ["0", "1"]:
            return False
    return True


# 检查是否存在重复坐标，快速判断识别错误
def check_answer(d: dict) -> bool:
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


if __name__ == "__main__":
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
        print("错误: 请设置 RAINYUN_USER 和 RAINYUN_PWD 环境变量")
        exit(1)

    # 以下为代码执行区域，请勿修改！
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    ver = "2.2"
    logger.info("------------------------------------------------------------------")
    logger.info(f"雨云签到工具 v{ver} by SerendipityR ~")
    logger.info("Github发布页: https://github.com/SerendipityR-2022/Rainyun-Qiandao")
    logger.info("------------------------------------------------------------------")
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
        logger.error("登录失败，退出程序")
        driver.quit()
        exit(1)
    
    logger.info("正在转到赚取积分页")
    driver.get("https://app.rainyun.com/account/reward/earn")
    driver.implicitly_wait(5)
    earn = driver.find_element(By.XPATH,
                               "//span[contains(text(), '每日签到')]/ancestor::div[1]//a[contains(text(), '领取奖励')]")
    logger.info("点击赚取积分")
    earn.click()
    logger.info("处理验证码")
    driver.switch_to.frame("tcaptcha_iframe_dy")
    process_captcha()
    driver.switch_to.default_content()
    driver.implicitly_wait(5)
    points_raw = driver.find_element(By.XPATH,
                                     '//*[@id="app"]/div[1]/div[3]/div[2]/div/div/div[2]/div[1]/div[1]/div/p/div/h3').get_attribute(
        "textContent")
    current_points = int(''.join(re.findall(r'\d+', points_raw)))
    logger.info(f"当前剩余积分: {current_points} | 约为 {current_points / 2000:.2f} 元")
    logger.info("任务执行成功！")
    driver.quit()

