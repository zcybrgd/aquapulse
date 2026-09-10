#!/usr/bin/env bash

# ============================================================================
# AquaPulse Core Stack Launcher
# ============================================================================

set -Eeuo pipefail

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VENV_DIR="$ROOT_DIR/.venv"
REQUIREMENTS_FILE="$ROOT_DIR/requirements.txt"

PLATFORM_DIR="$ROOT_DIR/plateform"
BACKEND_DIR="$PLATFORM_DIR/backend"
FRONTEND_DIR="$PLATFORM_DIR/frontend"

TESTBED_DIR="$ROOT_DIR/water-pipeline-testbed"
AGENT_DIR="$ROOT_DIR/agents/investigation_agent"

NETWORK_AGENT_DIR="$ROOT_DIR/agents/network_agent"
RESPONSE_AGENT_DIR="$ROOT_DIR/agents/response_agent"
NETWORK_AGENT_PORT=9001
NETWORK_RELEASE_PORT=8004
RESPONSE_AGENT_PORT=9002

PLATFORM_COMPOSE="$PLATFORM_DIR/docker-compose.yml"
TESTBED_COMPOSE="$TESTBED_DIR/docker-compose.yml"

BACKEND_PORT=8000
TESTBED_DASHBOARD_PORT=8080
AGENT_PORT=8002
FRONTEND_PORT=5173

# Host-local defaults for readiness probes. 127.0.0.1 is this process/container.
# If AquaPulse runs in Docker and agents are on the host or another service,
# set the URLs explicitly (Compose service name or host.docker.internal).
# Do not overwrite values already supplied by the operator.
INVESTIGATION_AGENT_PORT="${INVESTIGATION_AGENT_PORT:-${AGENT_PORT}}"
export INVESTIGATION_AGENT_URL="${INVESTIGATION_AGENT_URL:-http://127.0.0.1:${INVESTIGATION_AGENT_PORT:-8002}}"
export NETWORK_AGENT_URL="${NETWORK_AGENT_URL:-http://127.0.0.1:${NETWORK_AGENT_PORT:-9001}}"
export RESPONSE_AGENT_URL="${RESPONSE_AGENT_URL:-http://127.0.0.1:${RESPONSE_AGENT_PORT:-9002}}"
export AGENT_INTEGRATION_ENABLED="${AGENT_INTEGRATION_ENABLED:-false}"
export INVESTIGATION_AGENT_ENABLED="${INVESTIGATION_AGENT_ENABLED:-false}"
export NETWORK_AGENT_ENABLED="${NETWORK_AGENT_ENABLED:-false}"
export RESPONSE_AGENT_ENABLED="${RESPONSE_AGENT_ENABLED:-false}"
export AGENT_HEALTH_TIMEOUT_SECONDS="${AGENT_HEALTH_TIMEOUT_SECONDS:-2}"
export AGENT_HEALTH_CACHE_SECONDS="${AGENT_HEALTH_CACHE_SECONDS:-15}"
# Host port 6380 is the testbed Redis published by docker-compose (not Windows/WSL :6379).
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6380/0}"

INSTALL_DEPS=true

# ----------------------------------------------------------------------------
# Colors / Logging
# ----------------------------------------------------------------------------

if [[ -t 1 ]]; then
    RESET='\033[0m'
    BOLD='\033[1m'
    BLUE='\033[34m'
    GREEN='\033[32m'
    YELLOW='\033[33m'
    RED='\033[31m'
    CYAN='\033[36m'
else
    RESET=''
    BOLD=''
    BLUE=''
    GREEN=''
    YELLOW=''
    RED=''
    CYAN=''
fi

log() {
    echo -e "${BLUE}[SYSTEM]${RESET} $*"
}

success() {
    echo -e "${GREEN}[ OK ]${RESET} $*"
}

warning() {
    echo -e "${YELLOW}[WARN]${RESET} $*"
}

error() {
    echo -e "${RED}[ERROR]${RESET} $*" >&2
}

section() {
    echo
    echo -e "${BOLD}${CYAN}============================================================${RESET}"
    echo -e "${BOLD}${CYAN} $*${RESET}"
    echo -e "${BOLD}${CYAN}============================================================${RESET}"
}

# ----------------------------------------------------------------------------
# Error Handler
# ----------------------------------------------------------------------------

on_error() {
    local exit_code=$?
    local line_number=$1

    error "Startup failed at line ${line_number} (exit code: ${exit_code})."
    error "Check the output above for the actual failure."

    exit "$exit_code"
}

trap 'on_error $LINENO' ERR

# ----------------------------------------------------------------------------
# Parse Arguments
# ----------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        --no-install)
            INSTALL_DEPS=false
            shift
            ;;

        -h|--help)
            cat <<EOF

AquaPulse Core Stack Launcher

Usage:
    ./run.sh                 Start everything
    ./run.sh --no-install    Skip Python dependency installation
    ./run.sh --help          Show this help message

Services:
    Platform Backend    http://localhost:${BACKEND_PORT}
    Testbed Dashboard   http://localhost:${TESTBED_DASHBOARD_PORT}
    AIA Agent API       http://localhost:${AGENT_PORT}
    Network Agent       http://localhost:${NETWORK_AGENT_PORT}
    Network Release     http://localhost:${NETWORK_RELEASE_PORT}
    Response Agent      http://localhost:${RESPONSE_AGENT_PORT}
    Platform Frontend   http://localhost:${FRONTEND_PORT}

Docker:
    Platform Compose:
        ${PLATFORM_COMPOSE}

    Testbed Compose:
        ${TESTBED_COMPOSE}

EOF
            exit 0
            ;;

        *)
            error "Unknown argument: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# ----------------------------------------------------------------------------
# Banner
# ----------------------------------------------------------------------------

clear 2>/dev/null || true

echo
echo -e "${BOLD}${CYAN}"
echo "============================================================"
echo "              🚀 AquaPulse Core Stack"
echo "============================================================"
echo -e "${RESET}"

echo "Root directory: $ROOT_DIR"
echo

# ----------------------------------------------------------------------------
# 1. Validate Project Structure
# ----------------------------------------------------------------------------

section "1. Validating project structure"

REQUIRED_PATHS=(
    "$REQUIREMENTS_FILE"
    "$PLATFORM_COMPOSE"
    "$TESTBED_COMPOSE"
    "$BACKEND_DIR"
    "$FRONTEND_DIR"
    "$AGENT_DIR"
    "$NETWORK_AGENT_DIR"
)

for path in "${REQUIRED_PATHS[@]}"; do
    if [[ ! -e "$path" ]]; then
        error "Required path not found: $path"
        exit 1
    fi
done

success "Project structure looks valid."

# ----------------------------------------------------------------------------
# 2. Validate Required Commands
# ----------------------------------------------------------------------------

section "2. Checking required tools"

PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    error "Required command not found: python3 or python"
    exit 1
fi
success "Python executable found: $(command -v "$PYTHON_CMD")"

REQUIRED_COMMANDS=(
    docker
    npm
)

for cmd in "${REQUIRED_COMMANDS[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        error "Required command not found: $cmd"
        exit 1
    fi

    success "$cmd found: $(command -v "$cmd")"
done

# Check Docker daemon
if ! docker info >/dev/null 2>&1; then
    error "Docker daemon is not running."
    error "Start Docker and run this script again."
    exit 1
fi

success "Docker daemon is running."

# ----------------------------------------------------------------------------
# 3. Python Virtual Environment
# ----------------------------------------------------------------------------

section "3. Preparing Python environment"

if [[ ! -d "$VENV_DIR" ]]; then
    log "Virtual environment not found."
    log "Creating: $VENV_DIR"

    "$PYTHON_CMD" -m venv "$VENV_DIR"

    success "Virtual environment created."
else
    success "Virtual environment already exists."
fi

# shellcheck disable=SC1091
if [[ -f "$VENV_DIR/bin/activate" ]]; then
    source "$VENV_DIR/bin/activate"
elif [[ -f "$VENV_DIR/Scripts/activate" ]]; then
    source "$VENV_DIR/Scripts/activate"
else
    error "Could not find virtual environment activation script in $VENV_DIR"
    exit 1
fi

log "Python: $(python --version)"
log "Environment: $VIRTUAL_ENV"

# Nokia Network as Code for Network Health (reachability / location only).
# This is not CAMARA_ENABLED — actuation and valve commands stay off.
configure_nokia_network_health() {
    local root_env="$ROOT_DIR/.env"
    if [[ ! -f "$root_env" ]]; then
        log "Nokia/CAMARA Network Health: mock (no root .env)"
        return 0
    fi
    if ROOT_ENV_FILE="$root_env" python - <<'PY'
import os
from dotenv import dotenv_values

values = dotenv_values(os.environ["ROOT_ENV_FILE"])
key = (values.get("RAPIDAPI_KEY") or values.get("NOKIA_NETWORK_API_KEY") or "").strip().strip('"').strip("'")
raise SystemExit(0 if key else 1)
PY
    then
        export NOKIA_NETWORK_API_ENABLED="${NOKIA_NETWORK_API_ENABLED:-true}"
        export NOKIA_NETWORK_API_MODE="${NOKIA_NETWORK_API_MODE:-live}"
        export NOKIA_NETWORK_API_HOST="${NOKIA_NETWORK_API_HOST:-network-as-code.nokia.rapidapi.com}"
        export NOKIA_NETWORK_API_BASE_URL="${NOKIA_NETWORK_API_BASE_URL:-https://network-as-code.p-eu.rapidapi.com}"
        log "Nokia/CAMARA Network Health: live (RapidAPI key present; actuation flags unchanged)"
    else
        log "Nokia/CAMARA Network Health: mock (no RapidAPI key)"
    fi
}
configure_nokia_network_health

# ----------------------------------------------------------------------------
# 4. Python Dependencies
# ----------------------------------------------------------------------------

if [[ "$INSTALL_DEPS" == true ]]; then

    section "4. Checking Python dependencies"

    if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
        error "requirements.txt not found."
        exit 1
    fi

    log "Upgrading pip..."
    python -m pip install --upgrade pip --quiet

    log "Installing Python dependencies..."
    python -m pip install -r "$REQUIREMENTS_FILE"

    success "Python dependencies are ready."

else

    section "4. Python dependency installation skipped"

    warning "Running with --no-install."

fi

# ----------------------------------------------------------------------------
# 5. Start Docker Stacks
# ----------------------------------------------------------------------------

section "5. Starting Docker infrastructure"

log "Starting AquaPulse platform stack..."

if docker inspect aquapulse-db >/dev/null 2>&1; then
    if [[ "$(docker inspect -f '{{.State.Running}}' aquapulse-db)" == "true" ]]; then
        log "Reusing existing aquapulse-db container."
    else
        log "Starting existing aquapulse-db container..."
        docker start aquapulse-db >/dev/null
    fi
else
    docker compose \
        --env-file "$BACKEND_DIR/.env" \
        -f "$PLATFORM_COMPOSE" \
        up -d
fi

success "Platform Docker stack ready."

echo

log "Starting water pipeline testbed..."

# AquaPulse DB already binds host 5433. Skip testbed TimescaleDB to avoid that clash.
# Agents in this launcher use Redis + the simulator, not the AIA Timescale instance.
docker compose \
    -f "$TESTBED_COMPOSE" \
    up -d redis simulator dashboard

success "Water pipeline testbed started."

# ----------------------------------------------------------------------------
# 6. Show Docker Status
# ----------------------------------------------------------------------------

section "6. Docker stack status"

echo
echo "Platform:"
docker compose \
    -f "$PLATFORM_COMPOSE" \
    ps

echo
echo "Water Pipeline Testbed:"
docker compose \
    -f "$TESTBED_COMPOSE" \
    ps

# ----------------------------------------------------------------------------
# 7. Start Local Development Services
# ----------------------------------------------------------------------------

section "7. Starting local development services"

PIDS=()

start_service() {
    local name="$1"
    local directory="$2"
    shift 2

    log "Starting ${name}..."

    (
        cd "$directory"
        exec "$@"
    ) &

    local pid=$!
    PIDS+=("$pid")

    success "${name} started (PID ${pid})."
}

# Platform backend
start_service \
    "Platform Backend" \
    "$BACKEND_DIR" \
    uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --reload

# Investigation / AIA agent
start_service \
    "AIA Investigation Agent" \
    "$AGENT_DIR" \
    uvicorn aia.api:app \
    --host 0.0.0.0 \
    --port "$AGENT_PORT" \
    --reload

# Network Management Agent Release Server
start_service \
    "Network Agent Release Server" \
    "$NETWORK_AGENT_DIR" \
    env PYTHONPATH="$ROOT_DIR" uvicorn release_server:app \
    --host 0.0.0.0 \
    --port "$NETWORK_RELEASE_PORT" \
    --reload

# Network Management Agent Listener (Redis Bridge + /health on NETWORK_AGENT_PORT)
start_service \
    "Network Agent Listener" \
    "$ROOT_DIR" \
    env PYTHONPATH="$ROOT_DIR" NETWORK_AGENT_PORT="$NETWORK_AGENT_PORT" python "$NETWORK_AGENT_DIR/runner.py"

# Response Agent readiness API (health + contract only)
start_service \
    "Response Agent" \
    "$ROOT_DIR" \
    env PYTHONPATH="$ROOT_DIR" uvicorn agents.response_agent.api:app \
    --host 0.0.0.0 \
    --port "$RESPONSE_AGENT_PORT" \
    --reload

# Platform frontend (npx vite so host/port flags work on Windows npm)
start_service \
    "Platform Frontend" \
    "$FRONTEND_DIR" \
    npx vite --host 0.0.0.0 --port "$FRONTEND_PORT"

# ----------------------------------------------------------------------------
# 8. Startup Summary
# ----------------------------------------------------------------------------

section "AquaPulse is running"

cat <<EOF

${GREEN}Platform Backend:${RESET}
    http://localhost:${BACKEND_PORT}

${GREEN}Testbed Dashboard:${RESET}
    http://localhost:${TESTBED_DASHBOARD_PORT}

${GREEN}AIA Investigation Agent:${RESET}
    http://localhost:${AGENT_PORT}

${GREEN}Network Agent:${RESET}
    ${NETWORK_AGENT_URL}

${GREEN}Network Release Server:${RESET}
    http://localhost:${NETWORK_RELEASE_PORT}

${GREEN}Response Agent:${RESET}
    ${RESPONSE_AGENT_URL}

${GREEN}Platform Frontend:${RESET}
    http://localhost:${FRONTEND_PORT}

${CYAN}Docker infrastructure:${RESET}
    Platform stack       → running
    Water pipeline stack → running

${CYAN}Background Agents:${RESET}
    NMA Redis Listener   → active (listening on 'aia:results')

${YELLOW}Press Ctrl+C to stop the local development services.${RESET}

EOF

# ----------------------------------------------------------------------------
# 9. Graceful Shutdown
# ----------------------------------------------------------------------------

cleanup() {

    echo
    section "Shutting down AquaPulse"

    log "Stopping local development services..."

    for pid in "${PIDS[@]:-}"; do
        if kill -0 "$pid" 2>/dev/null; then
            log "Stopping process ${pid}..."
            kill "$pid" 2>/dev/null || true
        fi
    done

    # Give processes time to terminate gracefully
    sleep 1

    # Force kill anything still alive
    for pid in "${PIDS[@]:-}"; do
        if kill -0 "$pid" 2>/dev/null; then
            warning "Process ${pid} did not terminate gracefully. Killing..."
            kill -9 "$pid" 2>/dev/null || true
        fi
    done

    echo
    success "Local AquaPulse services stopped."

    echo
    log "Stopping Docker stacks..."
    docker compose -f "$PLATFORM_COMPOSE" down --remove-orphans || true
    docker compose -f "$TESTBED_COMPOSE" down --remove-orphans || true

    success "AquaPulse stack shutdown complete."

    exit 0
}

trap cleanup SIGINT SIGTERM

# ----------------------------------------------------------------------------
# 10. Monitor Services
# ----------------------------------------------------------------------------

while true; do

    for pid in "${PIDS[@]}"; do

        if ! kill -0 "$pid" 2>/dev/null; then
            warning "A local service (PID ${pid}) has stopped."

            cleanup
        fi

    done

    sleep 2

done