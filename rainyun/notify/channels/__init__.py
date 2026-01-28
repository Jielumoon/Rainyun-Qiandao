"""通知渠道实现。"""
import base64
import hashlib
import hmac
import json
import re
import time
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

import logging

import requests

# 配置 logger
logger = logging.getLogger(__name__)

from rainyun.notify.state import push_config


def _as_bool(value, default: bool = False) -> bool:
    """
    将环境变量字符串转换为布尔值。
    - 支持: true/false, 1/0, yes/no, on/off（大小写不敏感）
    - 传入 bool 时原样返回
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "no", "n", "off"}:
        return False
    return default


def post_with_retry(url: str, max_retries: int = 3, retry_delay: int = 2, **kwargs):
    """
    统一的 POST 重试封装。
    """
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            return requests.post(url, **kwargs)
        except requests.RequestException as e:
            last_error = e
            logger.warning(f"HTTP 请求异常（第{attempt}次）：{url} - {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
    raise last_error


def bark(title: str, content: str) -> None:
    """
    使用 bark 推送消息。
    """
    if not push_config.get("BARK_PUSH"):
        return
    logger.info("bark 服务启动")

    if push_config.get("BARK_PUSH").startswith("http"):
        url = f'{push_config.get("BARK_PUSH")}'
    else:
        url = f'https://api.day.app/{push_config.get("BARK_PUSH")}'

    bark_params = {
        "BARK_ARCHIVE": "isArchive",
        "BARK_GROUP": "group",
        "BARK_SOUND": "sound",
        "BARK_ICON": "icon",
        "BARK_LEVEL": "level",
        "BARK_URL": "url",
    }
    data = {
        "title": title,
        "body": content,
    }
    for pair in filter(
        lambda pairs: pairs[0].startswith("BARK_")
        and pairs[0] != "BARK_PUSH"
        and pairs[1]
        and bark_params.get(pairs[0]),
        push_config.items(),
    ):
        data[bark_params.get(pair[0])] = pair[1]
    headers = {"Content-Type": "application/json;charset=utf-8"}
    try:
        response = post_with_retry(
            url=url, data=json.dumps(data), headers=headers, timeout=15
        ).json()

        if response.get("code") == 200:
            logger.info("bark 推送成功！")
        else:
            logger.error(f"bark 推送失败！响应: {response}")
    except Exception as e:
        logger.error(f"bark 推送异常: {e}")


def console(title: str, content: str) -> None:
    """
    使用 控制台 推送消息。
    """
    logger.info(f"控制台通知:\n{title}\n\n{content}")


def dingding_bot(title: str, content: str) -> None:
    """
    使用 钉钉机器人 推送消息。
    """
    if not push_config.get("DD_BOT_SECRET") or not push_config.get("DD_BOT_TOKEN"):
        return
    logger.info("钉钉机器人 服务启动")

    timestamp = str(round(time.time() * 1000))
    secret_enc = push_config.get("DD_BOT_SECRET").encode("utf-8")
    string_to_sign = "{}\n{}".format(timestamp, push_config.get("DD_BOT_SECRET"))
    string_to_sign_enc = string_to_sign.encode("utf-8")
    hmac_code = hmac.new(
        secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    url = f'https://oapi.dingtalk.com/robot/send?access_token={push_config.get("DD_BOT_TOKEN")}&timestamp={timestamp}&sign={sign}'
    headers = {"Content-Type": "application/json;charset=utf-8"}
    data = {"msgtype": "text", "text": {"content": f"{title}\n\n{content}"}}
    try:
        response = post_with_retry(
            url=url, data=json.dumps(data), headers=headers, timeout=15
        ).json()

        if not response.get("errcode"):
            logger.info("钉钉机器人 推送成功！")
        else:
            logger.error(f"钉钉机器人 推送失败！响应: {response}")
    except Exception as e:
        logger.error(f"钉钉机器人 推送异常: {e}")


def feishu_bot(title: str, content: str) -> None:
    """
    使用 飞书机器人 推送消息。
    """
    if not push_config.get("FSKEY"):
        return
    logger.info("飞书 服务启动")

    url = f'https://open.feishu.cn/open-apis/bot/v2/hook/{push_config.get("FSKEY")}'
    data = {"msg_type": "text", "content": {"text": f"{title}\n\n{content}"}}

    if push_config.get("FSSECRET"):
        timestamp = str(int(time.time()))
        string_to_sign = f'{timestamp}\n{push_config.get("FSSECRET")}'
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        data["timestamp"] = timestamp
        data["sign"] = sign

    try:
        response = post_with_retry(url, data=json.dumps(data), timeout=15).json()

        if response.get("StatusCode") == 0 or response.get("code") == 0:
            logger.info("飞书 推送成功！")
        else:
            logger.error(f"飞书 推送失败！响应: {response}")
    except Exception as e:
        logger.error(f"飞书 推送异常: {e}")


def go_cqhttp(title: str, content: str) -> None:
    """
    使用 go_cqhttp 推送消息。
    """
    if not push_config.get("GOBOT_URL") or not push_config.get("GOBOT_QQ"):
        return
    logger.info("go-cqhttp 服务启动")

    url = f'{push_config.get("GOBOT_URL")}?access_token={push_config.get("GOBOT_TOKEN")}&{push_config.get("GOBOT_QQ")}&message=标题:{title}\n内容:{content}'
    try:
        response = requests.get(url, timeout=15).json()

        if response.get("status") == "ok":
            logger.info("go-cqhttp 推送成功！")
        else:
            logger.error(f"go-cqhttp 推送失败！响应: {response}")
    except Exception as e:
        logger.error(f"go-cqhttp 推送异常: {e}")


def gotify(title: str, content: str) -> None:
    """
    使用 gotify 推送消息。
    """
    if not push_config.get("GOTIFY_URL") or not push_config.get("GOTIFY_TOKEN"):
        return
    logger.info("gotify 服务启动")

    url = f'{push_config.get("GOTIFY_URL")}/message?token={push_config.get("GOTIFY_TOKEN")}'
    data = {
        "title": title,
        "message": content,
        "priority": push_config.get("GOTIFY_PRIORITY"),
    }
    try:
        response = post_with_retry(url, data=data, timeout=15).json()

        if response.get("id"):
            logger.info("gotify 推送成功！")
        else:
            logger.error(f"gotify 推送失败！响应: {response}")
    except Exception as e:
        logger.error(f"gotify 推送异常: {e}")


def iGot(title: str, content: str) -> None:
    """
    使用 iGot 推送消息。
    """
    if not push_config.get("IGOT_PUSH_KEY"):
        return
    logger.info("iGot 服务启动")

    url = f'https://push.hellyw.com/{push_config.get("IGOT_PUSH_KEY")}'
    data = {"title": title, "content": content}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = post_with_retry(url, data=data, headers=headers, timeout=15).json()

        if response.get("ret") == 0:
            logger.info("iGot 推送成功！")
        else:
            logger.error(f'iGot 推送失败！{response.get("errMsg")}')
    except Exception as e:
        logger.error(f"iGot 推送异常: {e}")


def serverJ(title: str, content: str) -> None:
    """
    通过 serverJ 推送消息。
    """
    if not push_config.get("PUSH_KEY"):
        return
    logger.info("serverJ 服务启动")

    data = {"text": title, "desp": content.replace("\n", "\n\n")}

    match = re.match(r"sctp(\d+)t", push_config.get("PUSH_KEY"))
    if match:
        num = match.group(1)
        url = f'https://{num}.push.ft07.com/send/{push_config.get("PUSH_KEY")}.send'
    else:
        url = f'https://sctapi.ftqq.com/{push_config.get("PUSH_KEY")}.send'

    try:
        response = post_with_retry(url, data=data, timeout=15).json()
        if response.get("errno") == 0 or response.get("code") == 0:
            logger.info("serverJ 推送成功！")
        else:
            logger.error(f'serverJ 推送失败！错误信息：{response.get("message", "未知错误")}')
    except Exception as e:
        logger.error(f"serverJ 推送异常: {e}")


def pushdeer(title: str, content: str) -> None:
    """
    通过PushDeer 推送消息
    """
    if not push_config.get("DEER_KEY"):
        return
    logger.info("PushDeer 服务启动")
    data = {
        "text": title,
        "desp": content,
        "type": "markdown",
        "pushkey": push_config.get("DEER_KEY"),
    }
    url = "https://api2.pushdeer.com/message/push"
    if push_config.get("DEER_URL"):
        url = push_config.get("DEER_URL")

    try:
        response = post_with_retry(url, data=data, timeout=15).json()
        # 安全取值：先检查 response 和 content
        content_res = response.get("content")
        if content_res and isinstance(content_res, dict) and len(content_res.get("result", [])) > 0:
            logger.info("PushDeer 推送成功！")
        else:
            logger.error(f"PushDeer 推送失败！响应: {response}")
    except Exception as e:
        logger.error(f"PushDeer 推送异常: {e}")


def chat(title: str, content: str) -> None:
    """
    通过Chat 推送消息
    """
    if not push_config.get("CHAT_URL") or not push_config.get("CHAT_TOKEN"):
        return
    logger.info("chat 服务启动")
    data = "payload=" + json.dumps({"text": title + "\n" + content})
    url = push_config.get("CHAT_URL") + push_config.get("CHAT_TOKEN")
    try:
        response = post_with_retry(url, data=data, timeout=15)
        if response.status_code == 200:
            logger.info("Chat 推送成功！")
        else:
            logger.error(f"Chat 推送失败！状态码: {response.status_code}")
    except Exception as e:
        logger.error(f"Chat 推送异常: {e}")


def pushplus_bot(title: str, content: str) -> None:
    """
    通过 pushplus 推送消息。
    """
    if not push_config.get("PUSH_PLUS_TOKEN"):
        return
    logger.info("PUSHPLUS 服务启动")

    url = "https://www.pushplus.plus/send"
    data = {
        "token": push_config.get("PUSH_PLUS_TOKEN"),
        "title": title,
        "content": content,
        "topic": push_config.get("PUSH_PLUS_USER"),
        "template": push_config.get("PUSH_PLUS_TEMPLATE"),
        "channel": push_config.get("PUSH_PLUS_CHANNEL"),
        "webhook": push_config.get("PUSH_PLUS_WEBHOOK"),
        "callbackUrl": push_config.get("PUSH_PLUS_CALLBACKURL"),
        "to": push_config.get("PUSH_PLUS_TO"),
    }
    body = json.dumps(data).encode(encoding="utf-8")
    headers = {"Content-Type": "application/json"}
    try:
        response = post_with_retry(url=url, data=body, headers=headers, timeout=15).json()

        code = response.get("code")
        if code == 200:
            logger.info(f"PUSHPLUS 推送请求成功，流水号: {response.get('data')}")
        elif code in [900, 903, 905, 999]:
            logger.error(f"PUSHPLUS 推送失败: {response.get('msg')}")
        else:
            # 备用接口
            url_old = "http://pushplus.hxtrip.com/send"
            headers["Accept"] = "application/json"
            response = post_with_retry(url=url_old, data=body, headers=headers, timeout=15).json()
            if response.get("code") == 200:
                logger.info("PUSHPLUS(hxtrip) 推送成功！")
            else:
                logger.error(f"PUSHPLUS 备用接口也失败了: {response}")
    except Exception as e:
        logger.error(f"PUSHPLUS 推送异常: {e}")


def weplus_bot(title: str, content: str) -> None:
    """
    通过 微加机器人 推送消息。
    """
    if not push_config.get("WE_PLUS_BOT_TOKEN"):
        return
    logger.info("微加机器人 服务启动")

    template = "txt"
    if len(content) > 800:
        template = "html"

    url = "https://www.weplusbot.com/send"
    data = {
        "token": push_config.get("WE_PLUS_BOT_TOKEN"),
        "title": title,
        "content": content,
        "template": template,
        "receiver": push_config.get("WE_PLUS_BOT_RECEIVER"),
        "version": push_config.get("WE_PLUS_BOT_VERSION"),
    }
    body = json.dumps(data).encode(encoding="utf-8")
    headers = {"Content-Type": "application/json"}
    try:
        response = post_with_retry(url=url, data=body, headers=headers, timeout=15).json()

        if response.get("code") == 200:
            logger.info("微加机器人 推送成功！")
        else:
            logger.error(f"微加机器人 推送失败！响应: {response}")
    except Exception as e:
        logger.error(f"微加机器人 推送异常: {e}")


def qmsg_bot(title: str, content: str) -> None:
    """
    使用 qmsg 推送消息。
    """
    if not push_config.get("QMSG_KEY") or not push_config.get("QMSG_TYPE"):
        return
    logger.info("qmsg 服务启动")

    url = f'https://qmsg.zendee.cn/{push_config.get("QMSG_TYPE")}/{push_config.get("QMSG_KEY")}'
    payload = {"msg": f'{title}\n\n{content.replace("----", "-")}'.encode("utf-8")}
    try:
        response = post_with_retry(url=url, params=payload, timeout=15).json()

        if response.get("code") == 0:
            logger.info("qmsg 推送成功！")
        else:
            logger.error(f'qmsg 推送失败！原因: {response.get("reason")}')
    except Exception as e:
        logger.error(f"qmsg 推送异常: {e}")


def wecom_app(title: str, content: str) -> None:
    """
    通过 企业微信 APP 推送消息。
    """
    if not push_config.get("QYWX_AM"):
        return
    QYWX_AM_AY = re.split(",", push_config.get("QYWX_AM"))
    # 修复：条件逻辑错误，应该是"长度不在 4~5 之间时报错"
    if not (4 <= len(QYWX_AM_AY) <= 5):
        logger.error("QYWX_AM 设置错误!!")
        return
    logger.info("企业微信 APP 服务启动")

    corpid = QYWX_AM_AY[0]
    corpsecret = QYWX_AM_AY[1]
    touser = QYWX_AM_AY[2]
    agentid = QYWX_AM_AY[3]
    try:
        media_id = QYWX_AM_AY[4]
    except IndexError:
        media_id = ""

    try:
        wx = WeCom(corpid, corpsecret, agentid)
        if not media_id:
            message = title + "\n\n" + content
            response = wx.send_text(message, touser)
        else:
            response = wx.send_mpnews(title, content, media_id, touser)

        if response == "ok":
            logger.info("企业微信推送成功！")
        else:
            logger.error(f"企业微信推送失败！响应: {response}")
    except Exception as e:
        logger.error(f"企业微信推送异常: {e}")


class WeCom:
    def __init__(self, corpid, corpsecret, agentid):
        self.CORPID = corpid
        self.CORPSECRET = corpsecret
        self.AGENTID = agentid
        self.ORIGIN = "https://qyapi.weixin.qq.com"
        if push_config.get("QYWX_ORIGIN"):
            self.ORIGIN = push_config.get("QYWX_ORIGIN")

    def get_access_token(self):
        url = f"{self.ORIGIN}/cgi-bin/gettoken"
        values = {
            "corpid": self.CORPID,
            "corpsecret": self.CORPSECRET,
        }
        req = post_with_retry(url, params=values, timeout=15)
        data = json.loads(req.text)
        return data["access_token"]

    def send_text(self, message, touser="@all"):
        send_url = (
            f"{self.ORIGIN}/cgi-bin/message/send?access_token={self.get_access_token()}"
        )
        send_values = {
            "touser": touser,
            "msgtype": "text",
            "agentid": self.AGENTID,
            "text": {"content": message},
            "safe": "0",
        }
        send_msges = bytes(json.dumps(send_values), "utf-8")
        respone = post_with_retry(send_url, data=send_msges, timeout=15)
        respone = respone.json()
        return respone["errmsg"]

    def send_mpnews(self, title, message, media_id, touser="@all"):
        send_url = (
            f"{self.ORIGIN}/cgi-bin/message/send?access_token={self.get_access_token()}"
        )
        send_values = {
            "touser": touser,
            "msgtype": "mpnews",
            "agentid": self.AGENTID,
            "mpnews": {
                "articles": [
                    {
                        "title": title,
                        "thumb_media_id": media_id,
                        "author": "Author",
                        "content_source_url": "",
                        "content": message.replace("\n", "<br/>"),
                        "digest": message,
                    }
                ]
            },
        }
        send_msges = bytes(json.dumps(send_values), "utf-8")
        respone = post_with_retry(send_url, data=send_msges, timeout=15)
        respone = respone.json()
        return respone["errmsg"]


def wecom_bot(title: str, content: str) -> None:
    """
    通过 企业微信机器人 推送消息。
    """
    if not push_config.get("QYWX_KEY"):
        return
    logger.info("企业微信机器人服务启动")

    origin = "https://qyapi.weixin.qq.com"
    if push_config.get("QYWX_ORIGIN"):
        origin = push_config.get("QYWX_ORIGIN")

    url = f"{origin}/cgi-bin/webhook/send?key={push_config.get('QYWX_KEY')}"
    headers = {"Content-Type": "application/json;charset=utf-8"}
    data = {"msgtype": "text", "text": {"content": f"{title}\n\n{content}"}}
    try:
        response = post_with_retry(
            url=url, data=json.dumps(data), headers=headers, timeout=15
        ).json()

        if response.get("errcode") == 0:
            logger.info("企业微信机器人推送成功！")
        else:
            logger.error(f"企业微信机器人推送失败！响应: {response}")
    except Exception as e:
        logger.error(f"企业微信机器人推送异常: {e}")


def telegram_bot(title: str, content: str) -> None:
    """
    使用 telegram 机器人 推送消息。
    """
    if not push_config.get("TG_BOT_TOKEN") or not push_config.get("TG_USER_ID"):
        return
    logger.info("tg 服务启动")

    if push_config.get("TG_API_HOST"):
        url = f"{push_config.get('TG_API_HOST')}/bot{push_config.get('TG_BOT_TOKEN')}/sendMessage"
    else:
        url = (
            f"https://api.telegram.org/bot{push_config.get('TG_BOT_TOKEN')}/sendMessage"
        )
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "chat_id": str(push_config.get("TG_USER_ID")),
        "text": f"{title}\n\n{content}",
        "disable_web_page_preview": "true",
    }
    proxies = None
    if push_config.get("TG_PROXY_HOST") and push_config.get("TG_PROXY_PORT"):
        if push_config.get("TG_PROXY_AUTH") is not None and "@" not in push_config.get(
            "TG_PROXY_HOST"
        ):
            push_config["TG_PROXY_HOST"] = (
                push_config.get("TG_PROXY_AUTH")
                + "@"
                + push_config.get("TG_PROXY_HOST")
            )
        proxyStr = "http://{}:{}".format(
            push_config.get("TG_PROXY_HOST"), push_config.get("TG_PROXY_PORT")
        )
        proxies = {"http": proxyStr, "https": proxyStr}
    try:
        response = post_with_retry(
            url=url, headers=headers, params=payload, proxies=proxies, timeout=15
        ).json()

        if response.get("ok"):
            logger.info("tg 推送成功！")
        else:
            logger.error(f"tg 推送失败！响应: {response}")
    except Exception as e:
        logger.error(f"tg 推送异常: {e}")


def aibotk(title: str, content: str) -> None:
    """
    使用 智能微秘书 推送消息。
    """
    if (
        not push_config.get("AIBOTK_KEY")
        or not push_config.get("AIBOTK_TYPE")
        or not push_config.get("AIBOTK_NAME")
    ):
        return
    logger.info("智能微秘书 服务启动")

    if push_config.get("AIBOTK_TYPE") == "room":
        url = "https://api-bot.aibotk.com/openapi/v1/chat/room"
        data = {
            "apiKey": push_config.get("AIBOTK_KEY"),
            "roomName": push_config.get("AIBOTK_NAME"),
            "message": {"type": 1, "content": f"【青龙快讯】\n\n{title}\n{content}"},
        }
    else:
        url = "https://api-bot.aibotk.com/openapi/v1/chat/contact"
        data = {
            "apiKey": push_config.get("AIBOTK_KEY"),
            "name": push_config.get("AIBOTK_NAME"),
            "message": {"type": 1, "content": f"【青龙快讯】\n\n{title}\n{content}"},
        }
    body = json.dumps(data).encode(encoding="utf-8")
    headers = {"Content-Type": "application/json"}
    try:
        response = post_with_retry(
            url=url, data=body, headers=headers, timeout=15
        ).json()
        if response.get("code") == 0:
            logger.info("智能微秘书 推送成功！")
        else:
            logger.error(f'智能微秘书 推送失败！错误: {response.get("error")}')
    except Exception as e:
        logger.error(f"智能微秘书 推送异常: {e}")


def smtp(title: str, content: str) -> None:
    """
    使用 SMTP 邮件 推送消息。
    """
    if (
        not push_config.get("SMTP_SERVER")
        or not push_config.get("SMTP_SSL")
        or not push_config.get("SMTP_EMAIL")
        or not push_config.get("SMTP_PASSWORD")
        or not push_config.get("SMTP_NAME")
    ):
        return
    logger.info("SMTP 邮件 服务启动")

    message = MIMEText(content, "plain", "utf-8")
    message["From"] = formataddr(
        (
            Header(push_config.get("SMTP_NAME"), "utf-8").encode(),
            push_config.get("SMTP_EMAIL"),
        )
    )
    message["To"] = formataddr(
        (
            Header(push_config.get("SMTP_NAME"), "utf-8").encode(),
            push_config.get("SMTP_EMAIL"),
        )
    )
    message["Subject"] = Header(title, "utf-8")

    try:
        smtp_server = (
            smtplib.SMTP_SSL(push_config.get("SMTP_SERVER"), timeout=15)
            if push_config.get("SMTP_SSL") == "true"
            else smtplib.SMTP(push_config.get("SMTP_SERVER"), timeout=15)
        )
        smtp_server.login(
            push_config.get("SMTP_EMAIL"), push_config.get("SMTP_PASSWORD")
        )
        smtp_server.sendmail(
            push_config.get("SMTP_EMAIL"),
            push_config.get("SMTP_EMAIL"),
            message.as_bytes(),
        )
        smtp_server.close()
        logger.info("SMTP 邮件 推送成功！")
    except Exception as e:
        logger.error(f"SMTP 邮件 推送失败！{e}")


def pushme(title: str, content: str) -> None:
    """
    使用 PushMe 推送消息。
    """
    if not push_config.get("PUSHME_KEY"):
        return
    logger.info("PushMe 服务启动")

    url = (
        push_config.get("PUSHME_URL")
        if push_config.get("PUSHME_URL")
        else "https://push.i-i.me/"
    )
    data = {
        "push_key": push_config.get("PUSHME_KEY"),
        "title": title,
        "content": content,
        "date": push_config.get("date") if push_config.get("date") else "",
        "type": push_config.get("type") if push_config.get("type") else "",
    }
    try:
        response = post_with_retry(url, data=data, timeout=15)
        if response.status_code == 200 and response.text == "success":
            logger.info("PushMe 推送成功！")
        else:
            logger.error(f"PushMe 推送失败！状态码: {response.status_code} 响应: {response.text}")
    except Exception as e:
        logger.error(f"PushMe 推送异常: {e}")


def chronocat(title: str, content: str) -> None:
    """
    使用 CHRONOCAT 推送消息。
    """
    if (
        not push_config.get("CHRONOCAT_URL")
        or not push_config.get("CHRONOCAT_QQ")
        or not push_config.get("CHRONOCAT_TOKEN")
    ):
        return

    logger.info("CHRONOCAT 服务启动")

    user_ids = re.findall(r"user_id=(\d+)", push_config.get("CHRONOCAT_QQ"))
    group_ids = re.findall(r"group_id=(\d+)", push_config.get("CHRONOCAT_QQ"))

    url = f'{push_config.get("CHRONOCAT_URL")}/api/message/send'
    headers = {
        "Content-Type": "application/json",
        "Authorization": f'Bearer {push_config.get("CHRONOCAT_TOKEN")}',
    }

    for chat_type, ids in [(1, user_ids), (2, group_ids)]:
        if not ids:
            continue
        for chat_id in ids:
            data = {
                "peer": {"chatType": chat_type, "peerUin": chat_id},
                "elements": [
                    {
                        "elementType": 1,
                        "textElement": {"content": f"{title}\n\n{content}"},
                    }
                ],
            }
            try:
                response = post_with_retry(
                    url, headers=headers, data=json.dumps(data), timeout=15
                )
                if response.status_code == 200:
                    logger.info(f"QQ消息({chat_id})推送成功！")
                else:
                    logger.error(f"QQ消息({chat_id})推送失败！状态码: {response.status_code}")
            except Exception as e:
                logger.error(f"QQ消息({chat_id})推送异常: {e}")


def ntfy(title: str, content: str) -> None:
    """
    通过 Ntfy 推送消息
    """

    def encode_rfc2047(text: str) -> str:
        """将文本编码为符合 RFC 2047 标准的格式"""
        encoded_bytes = base64.b64encode(text.encode("utf-8"))
        encoded_str = encoded_bytes.decode("utf-8")
        return f"=?utf-8?B?{encoded_str}?="

    if not push_config.get("NTFY_TOPIC"):
        return
    logger.info("ntfy 服务启动")
    priority = "3"
    if not push_config.get("NTFY_PRIORITY"):
        logger.warning("ntfy 服务的NTFY_PRIORITY 未设置!!默认设置为3")
    else:
        priority = push_config.get("NTFY_PRIORITY")

    # 使用 RFC 2047 编码 title
    encoded_title = encode_rfc2047(title)

    data = content.encode(encoding="utf-8")
    headers = {"Title": encoded_title, "Priority": priority, "Icon": "https://qn.whyour.cn/logo.png"}  # 使用编码后的 title
    if push_config.get("NTFY_TOKEN"):
        headers['Authorization'] = "Bearer " + push_config.get("NTFY_TOKEN")
    elif push_config.get("NTFY_USERNAME") and push_config.get("NTFY_PASSWORD"):
        authStr = push_config.get("NTFY_USERNAME") + ":" + push_config.get("NTFY_PASSWORD")
        headers['Authorization'] = "Basic " + base64.b64encode(authStr.encode('utf-8')).decode('utf-8')
    if push_config.get("NTFY_ACTIONS"):
        headers['Actions'] = encode_rfc2047(push_config.get("NTFY_ACTIONS"))

    url = push_config.get("NTFY_URL") + "/" + push_config.get("NTFY_TOPIC")
    try:
        response = post_with_retry(url, data=data, headers=headers, timeout=15)
        if response.status_code == 200:
            logger.info("Ntfy 推送成功！")
        else:
            logger.error(f"Ntfy 推送失败！状态码: {response.status_code} 响应: {response.text}")
    except Exception as e:
        logger.error(f"Ntfy 推送异常: {e}")


def wxpusher_bot(title: str, content: str) -> None:
    """
    通过 wxpusher 推送消息。
    支持的环境变量:
    - WXPUSHER_APP_TOKEN: appToken
    - WXPUSHER_TOPIC_IDS: 主题ID, 多个用英文分号;分隔
    - WXPUSHER_UIDS: 用户ID, 多个用英文分号;分隔
    """
    if not push_config.get("WXPUSHER_APP_TOKEN"):
        return

    url = "https://wxpusher.zjiecode.com/api/send/message"

    # 处理topic_ids和uids，将分号分隔的字符串转为数组
    topic_ids = []
    if push_config.get("WXPUSHER_TOPIC_IDS"):
        topic_ids = [
            int(id.strip())
            for id in push_config.get("WXPUSHER_TOPIC_IDS").split(";")
            if id.strip()
        ]

    uids = []
    if push_config.get("WXPUSHER_UIDS"):
        uids = [
            uid.strip()
            for uid in push_config.get("WXPUSHER_UIDS").split(";")
            if uid.strip()
        ]

    # topic_ids uids 至少有一个
    if not topic_ids and not uids:
        logger.warning("wxpusher 服务的 WXPUSHER_TOPIC_IDS 和 WXPUSHER_UIDS 至少设置一个!!")
        return

    logger.info("wxpusher 服务启动")

    data = {
        "appToken": push_config.get("WXPUSHER_APP_TOKEN"),
        "content": f"<h1>{title}</h1><br/><div style='white-space: pre-wrap;'>{content}</div>",
        "summary": title,
        "contentType": 2,
        "topicIds": topic_ids,
        "uids": uids,
        "verifyPayType": 0,
    }

    headers = {"Content-Type": "application/json"}
    try:
        response = post_with_retry(url=url, json=data, headers=headers, timeout=15).json()

        if response.get("code") == 1000:
            logger.info("wxpusher 推送成功！")
        else:
            logger.error(f"wxpusher 推送失败！原因: {response.get('msg')}")
    except Exception as e:
        logger.error(f"wxpusher 推送异常: {e}")


def parse_headers(headers):
    if not headers:
        return {}

    parsed = {}
    lines = headers.split("\n")

    for line in lines:
        i = line.find(":")
        if i == -1:
            continue

        key = line[:i].strip().lower()
        val = line[i + 1 :].strip()
        parsed[key] = parsed.get(key, "") + ", " + val if key in parsed else val

    return parsed


def parse_string(input_string, value_format_fn=None):
    matches = {}
    pattern = r"(\w+):\s*((?:(?!\n\w+:).)*)"
    regex = re.compile(pattern)
    for match in regex.finditer(input_string):
        key, value = match.group(1).strip(), match.group(2).strip()
        try:
            value = value_format_fn(value) if value_format_fn else value
            json_value = json.loads(value)
            matches[key] = json_value
        except:
            matches[key] = value
    return matches


def parse_body(body, content_type, value_format_fn=None):
    if not body or content_type == "text/plain":
        return value_format_fn(body) if value_format_fn and body else body

    parsed = parse_string(body, value_format_fn)

    if content_type == "application/x-www-form-urlencoded":
        data = urllib.parse.urlencode(parsed, doseq=True)
        return data

    if content_type == "application/json":
        data = json.dumps(parsed)
        return data

    return parsed


def custom_notify(title: str, content: str) -> None:
    """
    通过 自定义通知 推送消息。
    """
    if not push_config.get("WEBHOOK_URL") or not push_config.get("WEBHOOK_METHOD"):
        return

    logger.info("自定义通知服务启动")

    WEBHOOK_URL = push_config.get("WEBHOOK_URL")
    WEBHOOK_METHOD = push_config.get("WEBHOOK_METHOD")
    WEBHOOK_CONTENT_TYPE = push_config.get("WEBHOOK_CONTENT_TYPE")
    WEBHOOK_BODY = push_config.get("WEBHOOK_BODY")
    WEBHOOK_HEADERS = push_config.get("WEBHOOK_HEADERS")

    if "$title" not in WEBHOOK_URL and "$title" not in WEBHOOK_BODY:
        logger.warning("自定义通知请求头或者请求体中必须包含 $title 和 $content")
        return

    headers = parse_headers(WEBHOOK_HEADERS)
    body = parse_body(
        WEBHOOK_BODY,
        WEBHOOK_CONTENT_TYPE,
        lambda v: v.replace("$title", title.replace("\n", "\\n")).replace(
            "$content", content.replace("\n", "\\n")
        ),
    )
    formatted_url = WEBHOOK_URL.replace(
        "$title", urllib.parse.quote_plus(title)
    ).replace("$content", urllib.parse.quote_plus(content))
    try:
        response = requests.request(
            method=WEBHOOK_METHOD, url=formatted_url, headers=headers, timeout=15, data=body
        )

        if response.status_code == 200:
            logger.info("自定义通知推送成功！")
        else:
            logger.error(f"自定义通知推送失败！状态码: {response.status_code} 响应: {response.text}")
    except Exception as e:
        logger.error(f"自定义通知推送异常: {e}")


def one() -> str:
    """
    获取一条一言。
    :return:
    """
    try:
        url = "https://v1.hitokoto.cn/"
        res = requests.get(url, timeout=5).json()
        return res["hitokoto"] + "    ----" + res["from"]
    except Exception as e:
        logger.warning(f"获取一言失败 (拿不到就算了，不影响主流程): {e}")
        return ""


