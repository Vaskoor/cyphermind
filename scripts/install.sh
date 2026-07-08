#!/usr/bin/env bash
# CypherMind Installation Script
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "=============================="
echo " CypherMind Installation"
echo "=============================="

mkdir -p data/{nvd,cwe,chromadb,graphs,reports,selfplay,samples}

echo "[1/4] Python virtual environment..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install greenlet -q

echo "[2/4] Initializing database..."
export PYTHONPATH="$SCRIPT_DIR/backend"
python3 -c "
import asyncio, sys
sys.path.insert(0, '.')
from app.db.base import init_db
asyncio.run(init_db())
print('Database initialized.')
"

echo "[3/4] Initializing Q-table..."
python3 -c "
from app.learning.q_learning import q_orchestrator
print(f'Q-table: {len(q_orchestrator.q_table)} states')
"

echo "[4/4] Frontend dependencies..."
cd "$SCRIPT_DIR/frontend"
if command -v npm &>/dev/null; then
  npm install --legacy-peer-deps 2>/dev/null || npm install
else
  echo "  npm not found — install Node.js 18+ then run: cd frontend && npm install"
fi

echo ""
echo "=============================="
echo " Installation Complete!"
echo "=============================="
echo ""
echo "Start with: bash scripts/start.sh"
echo "  Frontend: http://localhost:3000"
echo "  API Docs: http://localhost:8000/docs"
