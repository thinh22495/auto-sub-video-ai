#!/bin/bash
# Setup script to download default models on first run.
# This script is optional — models can also be downloaded from the web UI.
#
# Usage:
#   docker compose exec autosub-app bash /app/scripts/setup_models.sh
#   # or locally:
#   ./scripts/setup_models.sh

set -e

echo "=== AutoSubAI Model Setup ==="
echo ""

# ── Ollama models ──────────────────────────────────────────────
OLLAMA_URL="${AUTOSUB_OLLAMA_BASE_URL:-http://autosub-ollama:11434}"
echo "[1/2] Checking Ollama at $OLLAMA_URL..."

ollama_ready=false
for i in $(seq 1 30); do
    if curl -sf "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
        echo "  Ollama is ready."
        ollama_ready=true
        break
    fi
    echo "  Waiting for Ollama... ($i/30)"
    sleep 2
done

if [ "$ollama_ready" = true ]; then
    DEFAULT_MODEL="${AUTOSUB_DEFAULT_OLLAMA_MODEL:-qwen2.5:7b}"
    echo "  Pulling Ollama model: $DEFAULT_MODEL (this may take a while)..."
    curl -sf "$OLLAMA_URL/api/pull" -d "{\"name\": \"$DEFAULT_MODEL\"}" | while read -r line; do
        status=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)
        if [ -n "$status" ]; then
            printf "\r  %s" "$status"
        fi
    done
    echo ""
    echo "  Model $DEFAULT_MODEL ready."
else
    echo "  WARNING: Ollama is not reachable at $OLLAMA_URL."
    echo "  Translation will not work until Ollama is running."
fi

# ── Whisper models ─────────────────────────────────────────────
echo ""
echo "[2/2] Whisper models"
echo "  Whisper models are downloaded automatically on first transcription."
echo "  Default model: ${AUTOSUB_DEFAULT_WHISPER_MODEL:-large-v3-turbo}"
echo "  Models are cached in: ${AUTOSUB_MODEL_DIR:-/data/models}/whisper/"

# ── Summary ────────────────────────────────────────────────────
echo ""
echo "=== Setup Complete ==="
echo "Access the web UI at http://localhost:${AUTOSUB_PORT:-8080}"
