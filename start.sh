#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Start the server
cd backend
python3 -m uvicorn server_api:app --host 0.0.0.0 --port ${PORT:-8000}
