#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "Starting Home Assistant Sandbox container..."
docker compose up -d

echo ""
echo "Home Assistant is starting up!"
echo "Open in your browser: http://localhost:8123"
echo "To view logs, run: docker compose logs -f"
