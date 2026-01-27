# 雨云自动签到 (Docker 版) v2.5

雨云每日自动签到工具，支持 ARM / AMD64 平台，Docker 一键部署。

## 功能特性

- ✅ 每日自动签到（验证码识别）
- ✅ 服务器到期检查
- ✅ 积分自动续费（到期前 7 天自动续费）
- ✅ Server酱 / Bark 等多渠道通知
- ✅ Docker 容器化部署

## 快速开始

```bash
# 1. 编辑 .env 文件
cp .env.example .env
# 填入 RAINYUN_USER 和 RAINYUN_PWD

# 2. 构建并运行
docker-compose up --build
```

## 环境变量

### 基础配置（必填）

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| RAINYUN_USER | ✅ | - | 雨云用户名 |
| RAINYUN_PWD | ✅ | - | 雨云密码 |
| TIMEOUT | ❌ | 15 | 页面加载超时(秒) |
| MAX_DELAY | ❌ | 90 | 随机延时上限(分钟) |
| DEBUG | ❌ | false | 调试模式（跳过延时） |

### 推送服务（可选）

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| PUSH_KEY | ❌ | - | Server酱推送密钥 |
| BARK_PUSH | ❌ | - | Bark 推送地址/设备码 |
| TG_BOT_TOKEN | ❌ | - | Telegram 机器人 token |
| TG_USER_ID | ❌ | - | Telegram 用户 ID |

> ℹ️ 只要配置了对应 key/必要字段即会启用，可同时配置多个；完整列表见 `.env.example` 的「推送服务」分组。
> 只需在 `.env` 中填写即可，`docker-compose.yml` 已通过 `env_file` 自动加载，无需逐条写到 `environment`。

### 自动续费（可选）

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| RAINYUN_API_KEY | ❌ | - | 雨云 API 密钥 |
| AUTO_RENEW | ❌ | true | 自动续费开关 |
| RENEW_THRESHOLD_DAYS | ❌ | 7 | 续费触发阈值(天) |
| RENEW_PRODUCT_IDS | ❌ | - | 续费白名单(逗号分隔产品ID) |

> 💡 **获取 API 密钥**：雨云后台 → 用户中心 → API 密钥
>
> 💰 **续费成本**：7天 = 2258 积分，签到每天 500 积分
>
> 🎯 **白名单模式**：设置 `RENEW_PRODUCT_IDS` 后只续费指定产品，留空则续费所有

### 高级配置（可选）

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| APP_VERSION | ❌ | 2.5 | 日志显示的版本号 |
| APP_BASE_URL | ❌ | https://app.rainyun.com | 雨云站点地址 |
| API_BASE_URL | ❌ | https://api.v2.rainyun.com | API 基础地址 |
| COOKIE_FILE | ❌ | cookies.json | 登录 Cookie 存储文件 |
| POINTS_TO_CNY_RATE | ❌ | 2000 | 积分兑换比例 |
| CAPTCHA_RETRY_LIMIT | ❌ | 5 | 验证码最大重试次数 |
| DOWNLOAD_TIMEOUT | ❌ | 10 | 图片下载超时(秒) |
| DOWNLOAD_MAX_RETRIES | ❌ | 3 | 图片下载最大重试次数 |
| DOWNLOAD_RETRY_DELAY | ❌ | 2 | 图片下载重试间隔(秒) |
| REQUEST_TIMEOUT | ❌ | 15 | API 请求超时(秒) |
| MAX_RETRIES | ❌ | 3 | API 请求最大重试次数 |
| RETRY_DELAY | ❌ | 2 | API 请求重试间隔(秒) |
| DEFAULT_RENEW_COST_7_DAYS | ❌ | 2258 | 续费价格兜底值 |

## 定时任务

```bash
# 每天早上 8 点执行
0 8 * * * docker compose -f /path/to/docker-compose.yml run --rm rainyun-qiandao
```

## 致谢

本项目基于以下仓库二次开发：

| 版本 | 作者 | 仓库 | 说明 |
|------|------|------|------|
| 原版 | SerendipityR | [Rainyun-Qiandao](https://github.com/SerendipityR-2022/Rainyun-Qiandao) | 初始 Python 版本 |
| 二改 | fatekey | [Rainyun-Qiandao](https://github.com/fatekey/Rainyun-Qiandao) | Docker 化改造 |
| 三改 | Jielumoon | 本仓库 | 稳定性优化 + 自动续费 |

## License

MIT
