#!/bin/bash
# Start the Campaign Builder worker server
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Install worker server dependencies
pip install -r worker_server/requirements.txt -q

# Start uvicorn
echo "Starting Campaign Builder worker on port 8787..."
uvicorn worker_server.main:app --host 0.0.0.0 --port 8787
