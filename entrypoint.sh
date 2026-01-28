#!/bin/sh
# 雨云自动签到启动脚本
# 支持两种运行模式：单次运行（默认）和定时模式
set -e

# 默认 cron 表达式（每天 8:00）
DEFAULT_SCHEDULE="0 8 * * *"

# 合法的 @ 表达式白名单（supercronic 支持的）
VALID_AT_EXPRESSIONS="@yearly @annually @monthly @weekly @daily @hourly"

if [ "$CRON_MODE" = "true" ]; then
    echo "=== 定时模式启用 ==="

    # 先去除可能的引号（兼容旧配置）
    CRON_SCHEDULE=$(echo "$CRON_SCHEDULE" | tr -d '"' | tr -d "'")

    # 去除首尾空格
    CRON_SCHEDULE=$(echo "$CRON_SCHEDULE" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    # 校验 CRON_SCHEDULE（去引号和空格后再判断）
    if [ -z "$CRON_SCHEDULE" ]; then
        echo "警告: CRON_SCHEDULE 未设置或为空，使用默认值: $DEFAULT_SCHEDULE"
        CRON_SCHEDULE="$DEFAULT_SCHEDULE"
    fi

    # 格式校验
    VALID=false

    # 检查是否为合法的 @ 表达式
    for expr in $VALID_AT_EXPRESSIONS; do
        if [ "$CRON_SCHEDULE" = "$expr" ]; then
            VALID=true
            break
        fi
    done

    # 如果不是 @ 表达式，检查是否为 5 段标准格式（至少 4 个空格）
    if [ "$VALID" = "false" ]; then
        SPACE_COUNT=$(echo "$CRON_SCHEDULE" | tr -cd ' ' | wc -c)
        if [ "$SPACE_COUNT" -ge 4 ]; then
            VALID=true
        fi
    fi

    # 校验失败，使用默认值
    if [ "$VALID" = "false" ]; then
        echo "错误: CRON_SCHEDULE 格式无效: $CRON_SCHEDULE"
        echo "期望格式: '分 时 日 月 周' 或 @daily/@hourly 等"
        echo "使用默认值: $DEFAULT_SCHEDULE"
        CRON_SCHEDULE="$DEFAULT_SCHEDULE"
    fi

    echo "执行计划: $CRON_SCHEDULE"
    echo "时区: $TZ"

    # 生成 crontab 文件（使用完整路径）
    echo "$CRON_SCHEDULE /usr/local/bin/python -u -m rainyun" > /app/crontab

    echo "=== Crontab 内容 ==="
    cat /app/crontab
    echo "===================="

    # 启动 supercronic
    # -passthrough-logs: 直接输出任务日志，不添加额外前缀
    exec supercronic -passthrough-logs /app/crontab
else
    # 单次运行模式（默认，兼容现有行为）
    exec python -u -m rainyun
fi
