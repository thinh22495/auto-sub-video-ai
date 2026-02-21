#!/bin/bash
# Docker health check script for AutoSubAI.
# Used in Dockerfile HEALTHCHECK directive.

set -e

API_URL="http://localhost:${AUTOSUB_PORT:-8000}/api/health"

response=$(curl -sf --max-time 5 "$API_URL" 2>/dev/null) || exit 1

# Check that API responded with a valid status
status=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null)

case "$status" in
    healthy|degraded)
        exit 0
        ;;
    *)
        exit 1
        ;;
esac
