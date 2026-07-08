#!/usr/bin/env bash
# Quick start script (development)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$SCRIPT_DIR/backend"

echo "Starting CypherMind (dev mode)..."

mkdir -p "$SCRIPT_DIR/data/chromadb"

# Backend
echo "Starting FastAPI backend on :8000..."
cd "$SCRIPT_DIR/backend"
source .venv/bin/activate 2>/dev/null || {
    echo "Run scripts/install.sh first"
    exit 1
}
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &>"$SCRIPT_DIR/data/backend.log" &
BACKEND_PID=$!

# Frontend
echo "Starting Next.js frontend on :3000..."
cd "$SCRIPT_DIR/frontend"
npm run dev &>"$SCRIPT_DIR/data/frontend.log" &
FRONTEND_PID=$!

sleep 3

echo ""
echo "=============================="
echo " CypherMind is running!"
echo "=============================="
echo "  Frontend:  http://localhost:3000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  Health:    http://localhost:8000/health"
echo ""
echo "  Logs: $SCRIPT_DIR/data/backend.log"
echo "        $SCRIPT_DIR/data/frontend.log"
echo ""
echo "Press Ctrl+C to stop"

cleanup() {
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM
wait
