#!/bin/bash
set -eu

# LEGACY ONLY. Docker Compose runs the scripts.runtime api command directly.
if [ "${RAPOT_ALLOW_LEGACY_PM2:-}" != "1" ]; then
  echo 'Legacy API launcher is disabled. Follow scripts/DEPLOY.md for Docker Compose.' >&2
  exit 1
fi

cd -- "$(dirname -- "$0")"
if [ ! -x .venv/bin/python ]; then
  echo 'Legacy launcher requires the reviewed project .venv/bin/python (Python 3.12.8).' >&2
  exit 1
fi

export RUN_EMBEDDED_BOT=false
exec .venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
