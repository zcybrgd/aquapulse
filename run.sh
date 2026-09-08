#!/usr/bin/env bash

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "================================================"
echo "      🚀 AquaPulse Core Stack Launcher"
echo "================================================"

# 1. Activate Python Virtual Environment
if [ -d ".venv" ]; then
    echo "[SYSTEM] Activating virtual environment (.venv)..."
    source .venv/bin/activate
else
    echo "[SYSTEM] Warning: .venv directory not found. Using system Python."
fi

# 2. Start Docker Containers (Platform DB + Testbed Stack)
echo "[SYSTEM] Starting Docker containers..."
docker compose -f plateform/docker-compose.yml up -d
docker compose -f water-pipeline-testbed/docker-compose.yml up -d

echo "[SYSTEM] Waiting 3 seconds for containers to initialize..."
sleep 3

# 3. Graceful Shutdown Handler (Catches Ctrl+C)
cleanup() {
    echo ""
    echo "[SYSTEM] Shutting down local services..."
    kill $(jobs -p) 2>/dev/null || true
    echo "[SYSTEM] AquaPulse stopped cleanly."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 4. Launch Local Development Services
echo "[SYSTEM] Spawning backend, agent, and frontend..."

(
    cd "$ROOT_DIR/plateform/backend"
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) &

(
    cd "$ROOT_DIR/agents/investigation_agent"
    uvicorn aia.api:app --host 0.0.0.0 --port 8002 --reload
) &

(
    cd "$ROOT_DIR/plateform/frontend"
    npm run dev
) &

echo "================================================"
echo "  All AquaPulse services are running!"
echo "  - Platform Backend:  http://localhost:8000"
echo "  - Testbed Dashboard: http://localhost:8080"
echo "  - AIA Agent API:     http://localhost:8002"
echo "  - Platform Frontend: http://localhost:5173"
echo ""
echo "  Press Ctrl+C to stop all local processes."
echo "================================================"

# Keep the script running to hold background processes
wait