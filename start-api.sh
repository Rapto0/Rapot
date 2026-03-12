#!/bin/bash
set -e
source /opt/rapot-venv/bin/activate
# PM2 cwd ile hizali: varsayilan sunucu dizini /root/Rapot.
# Fallback olarak script'in bulundugu dizine iner.
cd /root/Rapot 2>/dev/null || cd "$(dirname "$0")"
uvicorn api.main:app --host 0.0.0.0 --port 8000
