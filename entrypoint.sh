#!/bin/sh
# 雨云自动签到启动脚本
# 支持两种运行模式：Web 常驻与定时模式
set -e

WEB_ENABLED="${WEB_ENABLED:-true}"
WEB_HOST="${WEB_HOST:-0.0.0.0}"
WEB_PORT="${WEB_PORT:-8000}"

if [ "$CRON_MODE" = "true" ]; then
    if [ "$WEB_ENABLED" = "true" ]; then
        echo "=== Web 面板启动 ==="
        echo "地址: http://${WEB_HOST}:${WEB_PORT}"
        uvicorn rainyun.web.app:app --host "$WEB_HOST" --port "$WEB_PORT" &
    else
        echo "=== Web 面板已关闭 ==="
    fi
    echo "=== 定时模式启用 ==="
    /usr/local/bin/python -u -m rainyun.scheduler.cron_sync || echo "警告: cron 同步失败"
    echo "=== cron 守护进程启动 ==="
    exec /usr/sbin/cron -f
else
    if [ "$WEB_ENABLED" = "true" ]; then
        echo "=== Web 面板启动 ==="
        echo "地址: http://${WEB_HOST}:${WEB_PORT}"
        exec uvicorn rainyun.web.app:app --host "$WEB_HOST" --port "$WEB_PORT"
    fi
    echo "=== Web 面板已关闭，未启用定时模式，容器退出 ==="
    exit 0
fi
