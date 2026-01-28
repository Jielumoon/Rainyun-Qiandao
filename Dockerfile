# 使用 Python 基础镜像
FROM python:3.11-slim

# 设置时区为上海，防止定时任务时间错误
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装 Chromium 和依赖（支持 ARM 和 AMD64）
RUN apt-get update && apt-get install -y \
    ca-certificates \
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

# 安装 supercronic（容器定时任务调度器）
# 使用本地预编译的二进制文件，避免构建时依赖 GitHub
ARG TARGETARCH
COPY bin/supercronic-linux-${TARGETARCH} /usr/local/bin/supercronic
RUN chmod +x /usr/local/bin/supercronic

WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
# 升级 pip 并安装依赖（修复 metadata 损坏问题）
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --force-reinstall -r requirements.txt

# 复制应用代码
COPY rainyun/ ./rainyun/
COPY rainyun.py .
COPY config.py .
COPY notify.py .
COPY stealth.min.js .
COPY api_client.py .
COPY server_manager.py .
COPY entrypoint.sh .
# 转换 Windows 换行符为 Unix 格式，并设置执行权限
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# 设置环境变量默认值
ENV RAINYUN_USER=""
ENV RAINYUN_PWD=""
ENV TIMEOUT=15
ENV MAX_DELAY=90
ENV DEBUG=false
# Chrome 低内存模式（适用于 1核1G 小鸡）
ENV CHROME_LOW_MEMORY=false
# 服务器管理功能（可选）
ENV RAINYUN_API_KEY=""
ENV AUTO_RENEW=true
ENV RENEW_THRESHOLD_DAYS=7
ENV RENEW_PRODUCT_IDS=""
# 推送服务（示例）
ENV PUSH_KEY=""
# 定时模式配置
ENV CRON_MODE=false
ENV CRON_SCHEDULE="0 8 * * *"
# Chromium 路径（Debian 系统）
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 启动脚本（支持单次运行和定时模式）
CMD ["/app/entrypoint.sh"]
