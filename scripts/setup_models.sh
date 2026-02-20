#!/bin/bash
# Setup script to download default models on first run.
# This script is optional - models can also be downloaded from the web UI.

set -e

echo "=== AutoSubAI Model Setup ==="

# Check if Ollama is available
OLLAMA_URL="${AUTOSUB_OLLAMA_BASE_URL:-http://autosub-ollama:11434}"
echo "Checking Ollama at $OLLAMA_URL..."

for i in $(seq 1 30); do
    if curl -sf "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
        echo "Ollama is ready."
        break
    fi
    echo "Waiting for Ollama... ($i/30)"
    sleep 2
done

# Pull default translation model
DEFAULT_MODEL="${AUTOSUB_DEFAULT_OLLAMA_MODEL:-qwen2.5:7b}"
echo "Pulling Ollama model: $DEFAULT_MODEL"
curl -sf "$OLLAMA_URL/api/pull" -d "{\"name\": \"$DEFAULT_MODEL\"}" || echo "Warning: Failed to pull $DEFAULT_MODEL"

echo ""
echo "=== Setup Complete ==="
echo "Whisper models are downloaded automatically on first use."
echo "Access the web UI at http://localhost:${AUTOSUB_PORT:-8080}"
