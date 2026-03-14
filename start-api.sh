#!/bin/bash
set -e
# PM2 cwd ile hizali: varsayilan sunucu dizini /root/Rapot.
# Fallback olarak script'in bulundugu dizine iner.
cd /root/Rapot 2>/dev/null || cd "$(dirname "$0")"

# Sunucu ortamlarinda farkli venv yollarini destekle.
if [ -f /opt/rapot-venv/bin/activate ]; then
  source /opt/rapot-venv/bin/activate
elif [ -f /root/Rapot/.venv/bin/activate ]; then
  source /root/Rapot/.venv/bin/activate
elif [ -f /root/Rapot/venv/bin/activate ]; then
  source /root/Rapot/venv/bin/activate
elif [ -f /root/.venv/bin/activate ]; then
  source /root/.venv/bin/activate
fi

if command -v uvicorn >/dev/null 2>&1; then
  exec uvicorn api.main:app --host 0.0.0.0 --port 8000
else
  exec python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
fi
