#!/bin/bash

# Debug information
echo "Python version:"
python3 --version
echo "Pip version:"
python3 -m pip --version

# Install dependencies
pip install -r requirements.txt

# Verify critical packages are installed
echo "Checking if uvicorn is installed:"
python3 -c "import uvicorn; print('uvicorn found:', uvicorn.__version__)" || echo "uvicorn not found!"
echo "Checking if fastapi is installed:"
python3 -c "import fastapi; print('fastapi found:', fastapi.__version__)" || echo "fastapi not found!"

# Start the server
echo "Starting uvicorn..."
python3 -m uvicorn backend.server_api:app --host 0.0.0.0 --port ${PORT:-8000}
