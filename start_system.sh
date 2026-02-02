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
cd frontend
npm run dev &
UI_PID=$!
cd ..

# Robust Cleanup Function
cleanup() {
    echo "Stopping system..."
    kill -TERM "$API_PID" 2>/dev/null
    kill -TERM "$UI_PID" 2>/dev/null
    wait "$API_PID" "$UI_PID" 2>/dev/null
    echo "System stopped."
}

# Trap SIGINT (Ctrl+C) and EXIT
trap cleanup SIGINT EXIT

# 4. Wait for system processes
echo "System processes started. Press CTRL+C to stop everything."
wait $API_PID $UI_PID
