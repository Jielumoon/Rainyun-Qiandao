"""页面定位符。"""

from selenium.webdriver.common.by import By

# 定位符常量化 (让维护更简单)
XPATH_CONFIG = {
    "LOGIN_BTN": "//button[@type='submit' and contains(., '登') and contains(., '录')]",
    "SIGN_IN_BTN": "//div[contains(@class, 'card-header') and .//span[contains(text(), '每日签到')]]//a[contains(text(), '领取奖励')]",
    # “每日签到”卡片头部（不依赖按钮存在，用于读取当前状态文案）
    "SIGN_IN_HEADER": "//div[contains(@class, 'card-header') and .//span[contains(text(), '每日签到')]]",
    # 验证码相关定位符统一为 (By, selector) 结构，避免 ID/XPath 混用
    "CAPTCHA_SUBMIT": (By.XPATH, "//div[@id='tcStatus']/div[2]/div[2]/div/div"),
    "CAPTCHA_RELOAD": (By.ID, "reload"),
    "CAPTCHA_BG": (By.ID, "slideBg"),
    "CAPTCHA_OP": (By.ID, "tcOperation"),
    "CAPTCHA_IMG_INSTRUCTION": (By.XPATH, "//div[@id='instruction']//img"),
}
