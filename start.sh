#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "=== Starting GreenPulse ==="
if [ ! -d ".venv" ]; then
    echo "Setting up virtual environment..."
    python3 -m venv .venv 2>/dev/null || true
fi

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

python3 -m pip install -q -r requirements.txt 2>/dev/null || true
echo "Launching GreenPulse..."
python3 app.py
