#!/bin/bash

# 1. Start the Virtual Environment
source venv/bin/activate
pip install -q requests

# 2. Start the Backend API (Dashboard)
echo "Starting Dashboard API..."
python3 dashboard/api.py &
API_PID=$!

# 3. Start the Frontend (Next.js)
echo "Starting Dashboard UI..."
cd dashboard/frontend
npm run dev &
UI_PID=$!
cd ../..

# 4. Start the Trading Engine (Multi-Stock)
echo "Starting Multi-Stock Trading Engine..."
python3 main.py

# Cleanup on exit
trap "kill $API_PID $UI_PID" EXIT
