# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.11-slim

WORKDIR /app

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    DATABASE_URL=sqlite:////data/talent_agent.db \
    SEED_ON_START=true

# 只复制依赖，避免把构建层也带进运行镜像
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /data && chown -R appuser:appuser /data /app

COPY --chown=appuser:appuser . .

USER appuser

# SQLite 数据落在 /data，挂卷即可持久化
VOLUME ["/data"]

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

# SEED_ON_START=false 时跳过重建种子数据，适合接 MySQL 或已有数据的场景
CMD ["sh", "-c", "if [ \"$SEED_ON_START\" = \"true\" ]; then python seed_data.py; fi && uvicorn app.main:app --host ${APP_HOST} --port ${APP_PORT}"]
