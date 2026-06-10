#!/bin/bash
# CryptoBot Pro — Start Script

echo ""
echo "  ₿ CryptoBot Pro — Starting..."
echo ""

# Start backend
echo "  [1/2] Starting Python backend..."
cd backend
pip install -r requirements.txt -q
python main.py &
BACKEND_PID=$!
echo "  ✓ Backend running on http://localhost:8000"

# Start frontend
echo ""
echo "  [2/2] Starting React frontend..."
cd ../frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!
echo "  ✓ Frontend running on http://localhost:3000"

echo ""
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 Open: http://localhost:3000"
echo "  Demo login: demo / demo123"
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Press Ctrl+C to stop both servers"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
