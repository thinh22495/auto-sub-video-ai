# =============================================================================
# Stage 1: Frontend build
# =============================================================================
FROM node:22-alpine AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# =============================================================================
# Stage 2: Python dependencies
# Install on a CUDA-capable base so CTranslate2/faster-whisper can find CUDA libs
# =============================================================================
FROM nvidia/cuda:12.4.1-devel-ubuntu22.04 AS python-deps

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-dev python3.12-venv python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.12 /usr/bin/python3 \
    && ln -sf /usr/bin/python3 /usr/bin/python

WORKDIR /app
COPY backend/requirements.txt ./
RUN python3 -m pip install --no-cache-dir --prefix=/install -r requirements.txt

# =============================================================================
# Stage 3: Production image
# Uses nvidia/cuda runtime for GPU auto-detection. Falls back to CPU gracefully.
# =============================================================================
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS production

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    libcublas-12-4 \
    supervisor \
    curl \
    # Fonts for subtitle rendering (ASS/libass burn-in)
    fonts-liberation \
    fonts-noto-cjk \
    fonts-dejavu \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.12 /usr/bin/python3 \
    && ln -sf /usr/bin/python3 /usr/bin/python

WORKDIR /app

# Copy Python packages from deps stage
COPY --from=python-deps /install /usr/local

# Copy backend code
COPY backend/ ./backend/
COPY alembic.ini ./

# Copy built frontend (Next.js static export)
COPY --from=frontend-build /frontend/out ./frontend/out/

# Copy configuration files
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY scripts/ ./scripts/
RUN chmod +x ./scripts/*.sh 2>/dev/null || true

# Create data directories
RUN mkdir -p /data/videos /data/subtitles /data/output /data/models /data/db /tmp/autosub

# Whisper models cache dir
ENV HF_HOME=/data/models/huggingface

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
