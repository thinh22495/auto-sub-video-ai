#!/bin/bash
# Setup script to download default models on first run.
# This script is optional — models can also be downloaded from the web UI.
#
# Usage:
#   docker compose exec autosub-app bash /app/scripts/setup_models.sh
#   # or locally:
#   ./scripts/setup_models.sh

set -e

echo "=== Cài đặt Mô hình AutoSubAI ==="
echo ""

# ── Ollama models ──────────────────────────────────────────────
OLLAMA_URL="${AUTOSUB_OLLAMA_BASE_URL:-http://autosub-ollama:11434}"
echo "[1/2] Kiểm tra Ollama tại $OLLAMA_URL..."

ollama_ready=false
for i in $(seq 1 30); do
    if curl -sf "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
        echo "  Ollama đã sẵn sàng."
        ollama_ready=true
        break
    fi
    echo "  Đang chờ Ollama... ($i/30)"
    sleep 2
done

if [ "$ollama_ready" = true ]; then
    DEFAULT_MODEL="${AUTOSUB_DEFAULT_OLLAMA_MODEL:-qwen2.5:7b}"
    echo "  Đang tải mô hình Ollama: $DEFAULT_MODEL (có thể mất một lúc)..."
    curl -sf "$OLLAMA_URL/api/pull" -d "{\"name\": \"$DEFAULT_MODEL\"}" | while read -r line; do
        status=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)
        if [ -n "$status" ]; then
            printf "\r  %s" "$status"
        fi
    done
    echo ""
    echo "  Mô hình $DEFAULT_MODEL đã sẵn sàng."
else
    echo "  CẢNH BÁO: Không thể kết nối Ollama tại $OLLAMA_URL."
    echo "  Chức năng dịch sẽ không hoạt động cho đến khi Ollama chạy."
fi

# ── Whisper models ─────────────────────────────────────────────
echo ""
echo "[2/2] Mô hình Whisper"
echo "  Mô hình Whisper được tải tự động khi phiên âm lần đầu."
echo "  Mô hình mặc định: ${AUTOSUB_DEFAULT_WHISPER_MODEL:-large-v3-turbo}"
echo "  Mô hình được lưu tại: ${AUTOSUB_MODEL_DIR:-/data/models}/whisper/"

# ── Summary ────────────────────────────────────────────────────
echo ""
echo "=== Setup Complete ==="
echo "Access the web UI at http://localhost:${AUTOSUB_PORT:-8080}"
