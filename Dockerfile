# =============================================================================
# Stage 1: Frontend build
# =============================================================================
FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# =============================================================================
# Stage 2: Python dependencies
# Install on a CUDA-capable base so CTranslate2/faster-whisper can find CUDA libs
# =============================================================================
FROM nvidia/cuda:12.4.1-devel-ubuntu22.04 AS python-deps

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.13 python3.13-dev python3.13-venv \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.13 /usr/bin/python3 \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && python3 -m ensurepip --upgrade \
    && python3 -m pip install --upgrade pip

WORKDIR /app
COPY backend/requirements.txt ./
RUN python3 -m pip install --no-cache-dir --target=/install -r requirements.txt

# =============================================================================
# Stage 3: Production image
# Uses nvidia/cuda runtime for GPU auto-detection. Falls back to CPU gracefully.
# =============================================================================
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS production

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies + Node.js 22
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common ca-certificates gnupg curl \
    && add-apt-repository ppa:deadsnakes/ppa \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.13 \
    python3.13-venv \
    nodejs \
    nginx \
    ffmpeg \
    libsndfile1 \
    libcublas-12-4 \
    # Fonts for subtitle rendering (ASS/libass burn-in)
    fonts-liberation \
    fonts-noto-cjk \
    fonts-dejavu \
    fonts-freefont-ttf \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.13 /usr/bin/python3 \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && python3 -m ensurepip --upgrade \
    && python3 -m pip install --no-cache-dir supervisor

WORKDIR /app

# Copy Python packages from deps stage and set PYTHONPATH
COPY --from=python-deps /install /opt/python-packages/
ENV PYTHONPATH=/opt/python-packages

# Copy backend code
COPY backend/ ./backend/
COPY alembic.ini ./

# Copy built frontend (Next.js standalone)
COPY --from=frontend-build /frontend/.next/standalone ./frontend/
COPY --from=frontend-build /frontend/.next/static ./frontend/.next/static
COPY --from=frontend-build /frontend/public ./frontend/public/

# Copy configuration files
COPY nginx.conf /app/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY scripts/ ./scripts/
RUN chmod +x ./scripts/*.sh 2>/dev/null || true

# Create data directories
RUN mkdir -p /data/videos /data/subtitles /data/output /data/models /data/db /tmp/autosub

# Whisper models cache dir
ENV HF_HOME=/data/models/huggingface

EXPOSE 3000 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
