"""配置定义与解析。"""

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Mapping

logger = logging.getLogger(__name__)

# fmt: off
DEFAULT_PUSH_CONFIG = {
    'HITOKOTO': True,                  # 启用一言（随机句子）

    'BARK_PUSH': '',                    # bark IP 或设备码，例：https://api.day.app/DxHcxxxxxRxxxxxxcm/
    'BARK_ARCHIVE': '',                 # bark 推送是否存档
    'BARK_GROUP': '',                   # bark 推送分组
    'BARK_SOUND': '',                   # bark 推送声音
    'BARK_ICON': '',                    # bark 推送图标
    'BARK_LEVEL': '',                   # bark 推送时效性
    'BARK_URL': '',                     # bark 推送跳转URL

    'CONSOLE': False,                    # 控制台输出

    'DD_BOT_SECRET': '',                # 钉钉机器人的 DD_BOT_SECRET
    'DD_BOT_TOKEN': '',                 # 钉钉机器人的 DD_BOT_TOKEN

    'FSKEY': '',                        # 飞书机器人的 FSKEY
    'FSSECRET': '',                     # 飞书机器人的 FSSECRET，对应安全设置里的签名校验密钥

    'GOBOT_URL': '',                    # go-cqhttp
                                        # 推送到个人QQ：http://127.0.0.1/send_private_msg
                                        # 群：http://127.0.0.1/send_group_msg
    'GOBOT_QQ': '',                     # go-cqhttp 的推送群或用户
                                        # GOBOT_URL 设置 /send_private_msg 时填入 user_id=个人QQ
                                        #               /send_group_msg   时填入 group_id=QQ群
    'GOBOT_TOKEN': '',                  # go-cqhttp 的 access_token

    'GOTIFY_URL': '',                   # gotify地址,如https://push.example.de:8080
    'GOTIFY_TOKEN': '',                 # gotify的消息应用token
    'GOTIFY_PRIORITY': 0,               # 推送消息优先级,默认为0

    'IGOT_PUSH_KEY': '',                # iGot 聚合推送的 IGOT_PUSH_KEY

    'PUSH_KEY': '',                     # server 酱的 PUSH_KEY，兼容旧版与 Turbo 版

    'DEER_KEY': '',                     # PushDeer 的 PUSHDEER_KEY
    'DEER_URL': '',                     # PushDeer 的 PUSHDEER_URL

    'CHAT_URL': '',                     # synology chat url
    'CHAT_TOKEN': '',                   # synology chat token

    'PUSH_PLUS_TOKEN': '',              # pushplus 推送的用户令牌
    'PUSH_PLUS_USER': '',               # pushplus 推送的群组编码
    'PUSH_PLUS_TEMPLATE': 'html',       # pushplus 发送模板，支持html,txt,json,markdown,cloudMonitor,jenkins,route,pay
    'PUSH_PLUS_CHANNEL': 'wechat',      # pushplus 发送渠道，支持wechat,webhook,cp,mail,sms
    'PUSH_PLUS_WEBHOOK': '',            # pushplus webhook编码，可在pushplus公众号上扩展配置出更多渠道
    'PUSH_PLUS_CALLBACKURL': '',        # pushplus 发送结果回调地址，会把推送最终结果通知到这个地址上
    'PUSH_PLUS_TO': '',                 # pushplus 好友令牌，微信公众号渠道填写好友令牌，企业微信渠道填写企业微信用户id

    'WE_PLUS_BOT_TOKEN': '',            # 微加机器人的用户令牌
    'WE_PLUS_BOT_RECEIVER': '',         # 微加机器人的消息接收者
    'WE_PLUS_BOT_VERSION': 'pro',          # 微加机器人的调用版本

    'QMSG_KEY': '',                     # qmsg 酱的 QMSG_KEY
    'QMSG_TYPE': '',                    # qmsg 酱的 QMSG_TYPE

    'QYWX_ORIGIN': '',                  # 企业微信代理地址

    'QYWX_AM': '',                      # 企业微信应用

    'QYWX_KEY': '',                     # 企业微信机器人

    'TG_BOT_TOKEN': '',                 # tg 机器人的 TG_BOT_TOKEN，例：1407203283:AAG9rt-6RDaaX0HBLZQq0laNOh898iFYaRQ
    'TG_USER_ID': '',                   # tg 机器人的 TG_USER_ID，例：1434078534
    'TG_API_HOST': '',                  # tg 代理 api
    'TG_PROXY_AUTH': '',                # tg 代理认证参数
    'TG_PROXY_HOST': '',                # tg 机器人的 TG_PROXY_HOST
    'TG_PROXY_PORT': '',                # tg 机器人的 TG_PROXY_PORT

    'AIBOTK_KEY': '',                   # 智能微秘书 个人中心的apikey 文档地址：http://wechat.aibotk.com/docs/about
    'AIBOTK_TYPE': '',                  # 智能微秘书 发送目标 room 或 contact
    'AIBOTK_NAME': '',                  # 智能微秘书  发送群名 或者好友昵称和type要对应好

    'SMTP_SERVER': '',                  # SMTP 发送邮件服务器，形如 smtp.exmail.qq.com:465
    'SMTP_SSL': 'false',                # SMTP 发送邮件服务器是否使用 SSL，填写 true 或 false
    'SMTP_EMAIL': '',                   # SMTP 收发件邮箱，通知将会由自己发给自己
    'SMTP_PASSWORD': '',                # SMTP 登录密码，也可能为特殊口令，视具体邮件服务商说明而定
    'SMTP_NAME': '',                    # SMTP 收发件人姓名，可随意填写

    'PUSHME_KEY': '',                   # PushMe 的 PUSHME_KEY
    'PUSHME_URL': '',                   # PushMe 的 PUSHME_URL

    'CHRONOCAT_QQ': '',                 # qq号
    'CHRONOCAT_TOKEN': '',              # CHRONOCAT 的token
    'CHRONOCAT_URL': '',                # CHRONOCAT的url地址

    'WEBHOOK_URL': '',                  # 自定义通知 请求地址
    'WEBHOOK_BODY': '',                 # 自定义通知 请求体
    'WEBHOOK_HEADERS': '',              # 自定义通知 请求头
    'WEBHOOK_METHOD': '',               # 自定义通知 请求方法
    'WEBHOOK_CONTENT_TYPE': '',         # 自定义通知 content-type

    'NTFY_URL': '',                     # ntfy地址,如https://ntfy.sh
    'NTFY_TOPIC': '',                   # ntfy的消息应用topic
    'NTFY_PRIORITY':'3',                # 推送消息优先级,默认为3
    'NTFY_TOKEN': '',                   # 推送token,可选
    'NTFY_USERNAME': '',                # 推送用户名称,可选
    'NTFY_PASSWORD': '',                # 推送用户密码,可选
    'NTFY_ACTIONS': '',                 # 推送用户动作,可选

    'WXPUSHER_APP_TOKEN': '',           # wxpusher 的 appToken 官方文档: https://wxpusher.zjiecode.com/docs/ 管理后台: https://wxpusher.zjiecode.com/admin/
    'WXPUSHER_TOPIC_IDS': '',           # wxpusher 的 主题ID，多个用英文分号;分隔 topic_ids 与 uids 至少配置一个才行
    'WXPUSHER_UIDS': '',                # wxpusher 的 用户ID，多个用英文分号;分隔 topic_ids 与 uids 至少配置一个才行
}
# fmt: on


def _read_str(env: Mapping[str, str], name: str, default: str) -> str:
    value = env.get(name)
    if value is None or value == "":
        return default
    return value


def _read_int(env: Mapping[str, str], name: str, default: int) -> int:
    value = env.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Invalid config: {name} must be int, using default {default}")
        return default


def _read_float(env: Mapping[str, str], name: str, default: float) -> float:
    value = env.get(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning(f"Invalid config: {name} must be number, using default {default}")
        return default


def _read_bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    value = env.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in ("true", "1", "yes", "y", "on")


def _parse_int_list(value: str) -> tuple[list[int], bool]:
    if not value:
        return [], False
    results = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            results.append(int(item))
        except ValueError:
            logger.error("配置错误：RENEW_PRODUCT_IDS 格式无效，应为逗号分隔的数字，自动续费已禁用")
            return [], True
    return results, False


@dataclass(frozen=True)
class Config:
    app_base_url: str
    api_base_url: str
    app_version: str
    cookie_file: str
    points_to_cny_rate: int
    captcha_retry_limit: int
    captcha_retry_unlimited: bool
    request_timeout: int
    max_retries: int
    retry_delay: float
    download_timeout: int
    download_max_retries: int
    download_retry_delay: float
    chrome_low_memory: bool
    default_renew_cost_7_days: int
    timeout: int
    max_delay: int
    rainyun_user: str
    rainyun_pwd: str
    debug: bool
    linux_mode: bool
    rainyun_api_key: str
    auto_renew: bool
    renew_threshold_days: int
    renew_product_ids: list[int]
    renew_product_ids_parse_error: bool
    chrome_bin: str
    chromedriver_path: str
    skip_push_title: str
    push_config: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Config":
        if env is None:
            env = os.environ

        app_base_url = _read_str(env, "APP_BASE_URL", "https://app.rainyun.com").rstrip("/")
        api_base_url = _read_str(env, "API_BASE_URL", "https://api.v2.rainyun.com").rstrip("/")
        app_version = _read_str(env, "APP_VERSION", "2.5")
        cookie_file = _read_str(env, "COOKIE_FILE", "cookies.json")

        points_to_cny_rate = _read_int(env, "POINTS_TO_CNY_RATE", 2000)
        captcha_retry_limit = _read_int(env, "CAPTCHA_RETRY_LIMIT", 5)
        captcha_retry_unlimited = _read_bool(env, "CAPTCHA_RETRY_UNLIMITED", False)

        request_timeout = _read_int(env, "REQUEST_TIMEOUT", 15)
        max_retries = _read_int(env, "MAX_RETRIES", 3)
        retry_delay = _read_float(env, "RETRY_DELAY", 2)

        download_timeout = _read_int(env, "DOWNLOAD_TIMEOUT", 10)
        download_max_retries = _read_int(env, "DOWNLOAD_MAX_RETRIES", 3)
        download_retry_delay = _read_float(env, "DOWNLOAD_RETRY_DELAY", 2)

        chrome_low_memory = _read_bool(env, "CHROME_LOW_MEMORY", False)
        default_renew_cost_7_days = _read_int(env, "DEFAULT_RENEW_COST_7_DAYS", 2258)

        timeout = _read_int(env, "TIMEOUT", 15)
        max_delay = _read_int(env, "MAX_DELAY", 90)
        rainyun_user = _read_str(env, "RAINYUN_USER", "")
        rainyun_pwd = _read_str(env, "RAINYUN_PWD", "")
        debug = _read_bool(env, "DEBUG", False)
        linux_mode = _read_bool(env, "LINUX_MODE", True)
        rainyun_api_key = _read_str(env, "RAINYUN_API_KEY", "")

        auto_renew = _read_bool(env, "AUTO_RENEW", True)
        renew_threshold_days = _read_int(env, "RENEW_THRESHOLD_DAYS", 7)
        renew_product_ids, renew_product_ids_parse_error = _parse_int_list(
            _read_str(env, "RENEW_PRODUCT_IDS", "").strip()
        )

        chrome_bin = _read_str(env, "CHROME_BIN", "")
        chromedriver_path = _read_str(env, "CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
        skip_push_title = _read_str(env, "SKIP_PUSH_TITLE", "")

        push_config = DEFAULT_PUSH_CONFIG.copy()
        for key in push_config:
            value = env.get(key)
            if value:
                push_config[key] = value

        return cls(
            app_base_url=app_base_url,
            api_base_url=api_base_url,
            app_version=app_version,
            cookie_file=cookie_file,
            points_to_cny_rate=points_to_cny_rate,
            captcha_retry_limit=captcha_retry_limit,
            captcha_retry_unlimited=captcha_retry_unlimited,
            request_timeout=request_timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
            download_timeout=download_timeout,
            download_max_retries=download_max_retries,
            download_retry_delay=download_retry_delay,
            chrome_low_memory=chrome_low_memory,
            default_renew_cost_7_days=default_renew_cost_7_days,
            timeout=timeout,
            max_delay=max_delay,
            rainyun_user=rainyun_user,
            rainyun_pwd=rainyun_pwd,
            debug=debug,
            linux_mode=linux_mode,
            rainyun_api_key=rainyun_api_key,
            auto_renew=auto_renew,
            renew_threshold_days=renew_threshold_days,
            renew_product_ids=renew_product_ids,
            renew_product_ids_parse_error=renew_product_ids_parse_error,
            chrome_bin=chrome_bin,
            chromedriver_path=chromedriver_path,
            skip_push_title=skip_push_title,
            push_config=push_config,
        )


@lru_cache(maxsize=1)
def get_default_config() -> Config:
    return Config.from_env()


_DEFAULT_CONFIG = get_default_config()

APP_BASE_URL = _DEFAULT_CONFIG.app_base_url
API_BASE_URL = _DEFAULT_CONFIG.api_base_url
APP_VERSION = _DEFAULT_CONFIG.app_version
COOKIE_FILE = _DEFAULT_CONFIG.cookie_file

POINTS_TO_CNY_RATE = _DEFAULT_CONFIG.points_to_cny_rate
CAPTCHA_RETRY_LIMIT = _DEFAULT_CONFIG.captcha_retry_limit
CAPTCHA_RETRY_UNLIMITED = _DEFAULT_CONFIG.captcha_retry_unlimited

REQUEST_TIMEOUT = _DEFAULT_CONFIG.request_timeout
MAX_RETRIES = _DEFAULT_CONFIG.max_retries
RETRY_DELAY = _DEFAULT_CONFIG.retry_delay

DOWNLOAD_TIMEOUT = _DEFAULT_CONFIG.download_timeout
DOWNLOAD_MAX_RETRIES = _DEFAULT_CONFIG.download_max_retries
DOWNLOAD_RETRY_DELAY = _DEFAULT_CONFIG.download_retry_delay

# Chrome 低内存模式（适用于 1核1G 小鸡）
CHROME_LOW_MEMORY = _DEFAULT_CONFIG.chrome_low_memory

DEFAULT_RENEW_COST_7_DAYS = _DEFAULT_CONFIG.default_renew_cost_7_days
