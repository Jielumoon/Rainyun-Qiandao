# 雨云自动签到（Web 面板版）

雨云每日自动签到工具，Docker 一键部署，配置统一走 Web 面板，支持多账户与自动续费。

## 功能特性

- ✅ 多账户管理（账号/密码/API Key/续费白名单）
- ✅ 定时签到（容器内 cron）
- ✅ 服务器到期检查与自动续费
- ✅ 多渠道通知（Web 高级设置）
- ✅ Docker 容器化部署

## 快速开始（Docker）

```bash
# 1. 准备环境变量
cp .env.example .env

# 2. 构建并启动（Web + 定时）
docker compose -f docker-compose.yml -f docker-compose.cron.yml up -d --build
```

打开浏览器访问：
```
http://localhost:8000
```

首次登录会初始化管理密码，后续使用该密码登录。

## Web 面板说明

### 账户管理
- 添加账号、密码、API Key（用于服务器管理）
- 设置续费白名单（产品 ID 列表）
- 启用/禁用单个账户

### 系统设置
- 自动续费开关与阈值
- 定时表达式（cron），保存后自动写入 `/etc/cron.d/rainyun`

### 高级设置（建议）
- 通知配置（`notify_config` JSON）
- 跳过推送标题（换行分隔）
- 超时/重试/验证码/下载策略

通知配置示例：
```json
{
  "PUSH_KEY": "xxx",
  "TG_BOT_TOKEN": "xxx",
  "TG_USER_ID": "123456"
}
```

## 环境变量（仅运行层）

> 业务配置已全部迁移至 Web 面板，env 只保留运行/部署参数。

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| WEB_ENABLED | true | Web 面板开关 |
| WEB_HOST | 0.0.0.0 | Web 绑定地址 |
| WEB_PORT | 8000 | Web 端口 |
| DATA_PATH | data/config.json | 数据文件路径 |
| CRON_MODE | false | 定时模式开关（使用 cron compose 会自动启用） |
| CHROME_BIN | /usr/bin/chromium | Chromium 路径 |
| CHROMEDRIVER_PATH | /usr/bin/chromedriver | chromedriver 路径 |
| CHROME_LOW_MEMORY | false | 低内存模式 |

## 数据与备份

默认数据文件：`data/config.json`  
建议将 `./data` 挂载为 volume，避免容器重建丢失配置。

## 常见问题

### 一键签到报 “Unable to obtain driver for chrome”
请确认容器内存在 chromedriver，并配置正确路径：
```
CHROME_BIN=/usr/bin/chromium
CHROMEDRIVER_PATH=/usr/bin/chromedriver
```

### 修改 Web 设置后不生效
Web 设置会直接写入 `data/config.json`，无需重启容器。  
