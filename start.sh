#!/usr/bin/env bash
set -euo pipefail

export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
PORT=${PORT:-8501}

exec streamlit run streamlit_app.py \
    --server.port="${PORT}" \
    --server.address="0.0.0.0" \
    --server.headless=true
