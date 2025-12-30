# Rainyun-Qiandao

https://github.com/SerendipityR-2022/Rainyun-Qiandao 的 docker 版，在 arm 和 amd64 平台均可运行


## 食用方法

### 快速开始
```bash
# 编辑 .env 文件，填入你的雨云账号
# RAINYUN_USER=你的用户名
# RAINYUN_PWD=你的密码

# 构建并运行
docker-compose up --build
```

### 环境变量说明
| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| RAINYUN_USER | ✅ | - | 雨云用户名 |
| RAINYUN_PWD | ✅ | - | 雨云密码 |
| TIMEOUT | ❌ | 15 | 连接超时等待(秒) |
| MAX_DELAY | ❌ | 90 | 最大随机等待延时(分钟) |
| DEBUG | ❌ | false | 调试模式 |

### 定时任务 (Cron)
```bash
# 每天早上 8 点执行签到
0 8 * * * docker compose -f /path/to/docker-compose.yml run --rm rainyun-qiandao
```