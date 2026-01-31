#!/bin/sh
# 雨云自动签到启动脚本
# 支持两种运行模式：单次运行（默认）和定时模式
set -e

WEB_ENABLED="${WEB_ENABLED:-true}"
WEB_HOST="${WEB_HOST:-0.0.0.0}"
WEB_PORT="${WEB_PORT:-8000}"

start_web() {
    if [ "$WEB_ENABLED" = "true" ]; then
        echo "=== Web 面板启动 ==="
        echo "地址: http://${WEB_HOST}:${WEB_PORT}"
        uvicorn rainyun.web.app:app --host "$WEB_HOST" --port "$WEB_PORT" &
    else
        echo "=== Web 面板已关闭 ==="
    fi
}

start_web

if [ "$CRON_MODE" = "true" ]; then
    echo "=== 定时模式启用 ==="
    /usr/local/bin/python -u -m rainyun.scheduler.cron_sync || echo "警告: cron 同步失败"
    echo "=== cron 守护进程启动 ==="
    exec /usr/sbin/cron -f
else
    # 单次运行模式（默认，兼容现有行为）
    exec python -u -m rainyun
fi
