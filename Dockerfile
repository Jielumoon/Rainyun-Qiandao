# 使用 Python 基础镜像
FROM python:3.11-slim

# 安装 Chromium 和依赖（支持 ARM 和 AMD64）
RUN apt-get update && apt-get install -y \
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
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY rainyun.py .
COPY stealth.min.js .

# 设置环境变量默认值
ENV RAINYUN_USER=""
ENV RAINYUN_PWD=""
ENV TIMEOUT=15
ENV MAX_DELAY=90
ENV DEBUG=false
# Chromium 路径（Debian 系统）
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

CMD ["python", "rainyun.py"]
