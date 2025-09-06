#!/bin/bash
set -e

echo "=== E261 Voice Backend Startup ==="
echo "Python version:"
python3 --version

echo "Verifying critical packages are available..."
python3 -c "import uvicorn; print('✓ uvicorn version:', uvicorn.__version__)"
python3 -c "import fastapi; print('✓ fastapi version:', fastapi.__version__)"
python3 -c "import sys; print('✓ Python path:', sys.path[0:3])"

echo "Starting FastAPI server..."
exec python3 -m uvicorn backend.server_api:app --host 0.0.0.0 --port ${PORT:-8000}
