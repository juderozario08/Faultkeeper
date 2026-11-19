#!/usr/bin/env bash
# Stop everything started by start.sh. Data (database, models) is kept.
#
#   ./scripts/stop.sh              stop all services
#   ./scripts/stop.sh --wipe-data  also delete the database and model volumes
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

case "$(uname -s)" in
  MINGW* | MSYS* | CYGWIN*)
    args=()
    [ "${1:-}" = "--wipe-data" ] && args=("-WipeData")
    exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$ROOT/scripts/stop.ps1" ${args[@]+"${args[@]}"}
    ;;
esac

WIPE=0
for arg in "$@"; do
  case "$arg" in
    --wipe-data) WIPE=1 ;;
    -h | --help) sed -n '2,5p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

for name in dashboard buggy-shop; do
  pidfile="$ROOT/.run/$name.pid"
  if [ -f "$pidfile" ]; then
    pid="$(cat "$pidfile")"
    if kill "$pid" 2>/dev/null; then echo "Stopped $name (pid $pid)"; fi
    rm -f "$pidfile"
  fi
done

if docker info >/dev/null 2>&1; then
  if [ "$WIPE" = 1 ]; then
    docker compose --profile ai down -v
    echo "Containers stopped and data volumes deleted."
  else
    docker compose --profile ai down
    echo "Containers stopped. Data is kept."
  fi
else
  echo "Docker isn't running; nothing to stop there."
fi
