#!/usr/bin/env bash
# Start everything: backend stack (Docker), dashboard and Buggy Shop (Vite).
#
#   ./scripts/start.sh            start (installs dependencies on first run)
#   ./scripts/start.sh --ai       also run Ollama in Docker and pull the default model
#   ./scripts/start.sh --reset    clear demo issues after starting
#   ./scripts/start.sh --no-open  don't open the browser
#
# macOS and Linux. On Windows use scripts\start.cmd (this script forwards to it from Git Bash).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

case "$(uname -s)" in
  MINGW* | MSYS* | CYGWIN*)
    args=()
    for arg in "$@"; do
      case "$arg" in
        --ai) args+=("-Ai") ;;
        --reset) args+=("-Reset") ;;
        --no-open) args+=("-NoOpen") ;;
      esac
    done
    exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$ROOT/scripts/start.ps1" ${args[@]+"${args[@]}"}
    ;;
esac

AI=0
RESET=0
OPEN=1
for arg in "$@"; do
  case "$arg" in
    --ai) AI=1 ;;
    --reset) RESET=1 ;;
    --no-open) OPEN=0 ;;
    -h | --help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

RUN="$ROOT/.run"
mkdir -p "$RUN"
MODEL="${INSIGHTS_MODEL:-qwen2.5-coder:3b}"

step() { printf '\n\033[1;35m==>\033[0m %s\n' "$1"; }
fail() { printf '\033[1;31mError:\033[0m %s\n' "$1" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || fail "$1 is not installed. $2"; }
up() { curl -fs -o /dev/null --max-time 3 "$1"; }

wait_for() { # url, seconds, label
  local url="$1" seconds="$2" label="$3" i
  for ((i = 0; i < seconds; i++)); do
    if up "$url"; then return 0; fi
    sleep 1
  done
  fail "$label did not become ready at $url (check: docker compose logs)"
}

step "Checking prerequisites"
need docker "Install Docker Desktop: https://www.docker.com/products/docker-desktop/"
need node "Install Node.js 20 or newer: https://nodejs.org"
need npm "It ships with Node.js: https://nodejs.org"
need curl "Install curl with your package manager."

if ! docker info >/dev/null 2>&1; then
  if [ "$(uname -s)" = "Darwin" ]; then
    echo "Starting Docker Desktop..."
    open -a Docker || true
  else
    echo "Docker isn't running. Start it (e.g. 'sudo systemctl start docker' or open Docker Desktop)."
  fi
  for ((i = 0; i < 120; i++)); do
    docker info >/dev/null 2>&1 && break
    sleep 1
  done
  docker info >/dev/null 2>&1 || fail "Docker is not running."
fi
echo "Docker, Node $(node --version) OK"

[ -f .env ] || { cp .env.example .env; echo "Created .env from .env.example"; }

step "Installing JavaScript dependencies (first run only)"
for app in frontend demo/buggy-shop; do
  if [ ! -d "$app/node_modules" ]; then
    (cd "$app" && npm ci --no-audit --no-fund)
  else
    echo "$app: already installed"
  fi
done

step "Starting backend services (Docker)"
profiles=()
[ "$AI" = 1 ] && profiles=(--profile ai)
docker compose ${profiles[@]+"${profiles[@]}"} up -d --build
echo "Waiting for the API..."
wait_for "http://localhost:8000/api/0/health/" 180 "The API"
echo "API is healthy"

if [ "$AI" = 1 ]; then
  step "Pulling the Insights model ($MODEL), first run can take a few minutes"
  docker compose exec -T ollama ollama pull "$MODEL"
fi

if [ "$RESET" = 1 ]; then
  step "Clearing demo issues"
  docker compose exec -T web python manage.py reset_demo
fi

start_vite() { # name, directory, port
  local name="$1" dir="$2" port="$3"
  if up "http://localhost:$port/"; then
    echo "$name already running on :$port"
    return
  fi
  (cd "$dir" && nohup node node_modules/vite/bin/vite.js >"$RUN/$name.log" 2>&1 &
    echo $! >"$RUN/$name.pid")
  wait_for "http://localhost:$port/" 60 "$name"
  echo "$name running on :$port (log: .run/$name.log)"
}

step "Starting the dashboard and the Buggy Shop"
start_vite dashboard frontend 5173
start_vite buggy-shop demo/buggy-shop 5174

if [ "$AI" = 0 ]; then
  if up "http://localhost:11434/api/tags"; then
    echo "Ollama detected on :11434 (Issue Insights enabled)"
  else
    echo "Tip: install Ollama (https://ollama.com) and run 'ollama pull $MODEL' to enable Issue Insights."
  fi
fi

cat <<EOF

Faultkeeper is running
  Dashboard   http://localhost:5173   (admin@faultkeeper.local / faultkeeper)
  Buggy Shop  http://localhost:5174   (click "Break things")
  Demo API    http://localhost:5175
  Admin       http://localhost:8000/admin/

Stop everything with: ./scripts/stop.sh
EOF

if [ "$OPEN" = 1 ]; then
  opener=""
  command -v open >/dev/null 2>&1 && opener="open"
  command -v xdg-open >/dev/null 2>&1 && opener="xdg-open"
  if [ -n "$opener" ]; then
    "$opener" "http://localhost:5174" >/dev/null 2>&1 || true
    "$opener" "http://localhost:5173" >/dev/null 2>&1 || true
  fi
fi
