#!/usr/bin/env bash

# ============================================================================
# AquaPulse Core Stack Launcher
# ============================================================================
#
# Starts:
#   - Platform Docker stack
#   - Water pipeline testbed Docker stack
#   - Platform backend
#   - Investigation / AIA agent
#   - Platform frontend
#
# Usage:
#   ./start.sh
#   ./start.sh --no-install
#
# Stop local development services:
#   Ctrl+C
#
# Stop Docker stacks separately:
#   docker compose -f plateform/docker-compose.yml down
#   docker compose -f water-pipeline-testbed/docker-compose.yml down
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

PLATFORM_COMPOSE="$PLATFORM_DIR/docker-compose.yml"
TESTBED_COMPOSE="$TESTBED_DIR/docker-compose.yml"

BACKEND_PORT=8000
TESTBED_DASHBOARD_PORT=8080
AGENT_PORT=8002
FRONTEND_PORT=5173

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
    ./start.sh                 Start everything
    ./start.sh --no-install    Skip Python dependency installation
    ./start.sh --help          Show this help message

Services:
    Platform Backend    http://localhost:${BACKEND_PORT}
    Testbed Dashboard   http://localhost:${TESTBED_DASHBOARD_PORT}
    AIA Agent API       http://localhost:${AGENT_PORT}
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

REQUIRED_COMMANDS=(
    python3
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

    python3 -m venv "$VENV_DIR"

    success "Virtual environment created."
else
    success "Virtual environment already exists."
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

log "Python: $(python --version)"
log "Environment: $VIRTUAL_ENV"

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

docker compose \
    -f "$PLATFORM_COMPOSE" \
    up -d --build

success "Platform Docker stack started."

echo

log "Starting water pipeline testbed..."

docker compose \
    -f "$TESTBED_COMPOSE" \
    up -d --build

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

# Platform frontend
start_service \
    "Platform Frontend" \
    "$FRONTEND_DIR" \
    npm run dev \
    -- \
    --host 0.0.0.0 \
    --port "$FRONTEND_PORT"

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

${GREEN}Platform Frontend:${RESET}
    http://localhost:${FRONTEND_PORT}

${CYAN}Docker infrastructure:${RESET}
    Platform stack       → running
    Water pipeline stack → running

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
    warning "Docker containers were NOT stopped."
    echo "To stop them manually:"
    echo
    echo "  docker compose -f plateform/docker-compose.yml down"
    echo "  docker compose -f water-pipeline-testbed/docker-compose.yml down"
    echo

    exit 0
}

trap cleanup SIGINT SIGTERM

# ----------------------------------------------------------------------------
# 10. Monitor Services
# ----------------------------------------------------------------------------

# Wait for any child process.
# If one unexpectedly exits, stop the entire local stack.

while true; do

    for pid in "${PIDS[@]}"; do

        if ! kill -0 "$pid" 2>/dev/null; then
            warning "A local service (PID ${pid}) has stopped."

            cleanup
        fi

    done

    sleep 2

done