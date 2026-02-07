#!/bin/bash
source /opt/rapot-venv/bin/activate
cd /home/user/Rapot
uvicorn api.main:app --host 0.0.0.0 --port 8000
