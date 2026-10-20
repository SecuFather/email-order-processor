#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="$1"

npm --prefix frontend run build

mkdir -p "$TARGET_DIR/frontend"
cp main.py api.py db.py config.py schemas.py llm.py gus.py fakturownia.py pyproject.toml uv.lock .python-version "$TARGET_DIR/"
cp -R frontend/dist "$TARGET_DIR/frontend/"

cd "$TARGET_DIR"
set -a
source .env
set +a

tailscale cert --cert-file "$SSL_CERTFILE" --key-file "$SSL_KEYFILE" "$TAILSCALE_DOMAIN"
uv sync --frozen
