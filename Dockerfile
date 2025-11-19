# イメージの作成

# ── Stage 1: Builder (依存関係のビルド) ──
FROM python:3.12-slim AS builder
WORKDIR /app

# pip 周りのパフォーマンスチューニング
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# ビルド依存のみインストール
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libgomp1 curl\
 && rm -rf /var/lib/apt/lists/*

# 依存リストをコピーして wheel 化
COPY ./requirements.txt .
RUN pip install --upgrade pip \
 && pip wheel --wheel-dir /wheels -r requirements.txt

# ── Stage 2: Runtime (実行用イメージ) ──
FROM python:3.12-slim AS runner
WORKDIR /app

# 最小限のランタイム依存のみを残す
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 awscli curl\
 && rm -rf /var/lib/apt/lists/*

# wheel を使って依存をインストール（ビルドツールは含まれない）
COPY --from=builder /wheels /wheels
COPY ./requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
 && rm -rf /wheels

# アプリケーションコードを配置
COPY backend /app

# セキュリティ向上のため非 root ユーザーを作成
RUN useradd --create-home appuser
USER appuser

# 環境変数
ENV PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    LOG_LEVEL=info
