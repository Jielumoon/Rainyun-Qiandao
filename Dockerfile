# 使用 Python 基础镜像
FROM python:3.11-slim

# 设置时区为上海，防止定时任务时间错误
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装 Chromium 和依赖（支持 ARM 和 AMD64）
RUN apt-get update && apt-get install -y \
    ca-certificates \
    cron \
    chromium \
    chromium-driver \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    libgl1 \
    libgbm1 \
    libasound2t64 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
# 升级 pip 并安装依赖（修复 metadata 损坏问题）
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --force-reinstall -r requirements.txt

# 复制应用代码
COPY rainyun/ ./rainyun/
COPY stealth.min.js .
COPY entrypoint.sh .
# 转换 Windows 换行符为 Unix 格式，并设置执行权限
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# 仅保留运行层环境变量（业务配置全部走 Web 面板）
# 定时模式配置（默认开启）
ENV CRON_MODE=true
# Chromium 路径（Debian 系统）
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
# Chrome 低内存模式（适用于 1核1G 小鸡）
ENV CHROME_LOW_MEMORY=false
# Web 面板配置
ENV WEB_ENABLED=true
ENV WEB_HOST=0.0.0.0
ENV WEB_PORT=8000
ENV DATA_PATH=data/config.json

EXPOSE 8000

# 启动脚本（Web 面板 / 定时模式）
CMD ["/app/entrypoint.sh"]
