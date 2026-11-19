#!/usr/bin/env bash
# Run every check: lint, types, tests, builds, Docker smoke test, end-to-end ingest, production image.
#
#   ./scripts/check.sh                 everything (needs Docker for the last steps)
#   ./scripts/check.sh --quick         lint, types, unit tests and builds only (no Docker)
#   ./scripts/check.sh --install-hook  run the quick checks automatically before every git push
#
# macOS and Linux. On Windows use scripts\check.cmd (this script forwards to it from Git Bash).
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

case "$(uname -s)" in
  MINGW* | MSYS* | CYGWIN*)
    args=()
    for arg in "$@"; do
      case "$arg" in
        --quick) args+=("-Quick") ;;
        --install-hook) args+=("-InstallHook") ;;
      esac
    done
    exec powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$ROOT/scripts/check.ps1" ${args[@]+"${args[@]}"}
    ;;
esac

QUICK=0
for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=1 ;;
    --install-hook)
      hook="$ROOT/.git/hooks/pre-push"
      printf '#!/bin/sh\n# Installed by scripts/check.sh: quick checks before every push.\nexec "$(git rev-parse --show-toplevel)/scripts/check.sh" --quick\n' >"$hook"
      chmod +x "$hook"
      echo "Installed pre-push hook: quick checks now run before every 'git push'."
      exit 0
      ;;
    -h | --help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

names=()
results=()
started=$SECONDS

run() { # label, command...
  local label="$1"; shift
  printf '\n\033[1;35m==>\033[0m %s\n' "$label"
  local t=$SECONDS
  if "$@"; then
    names+=("$label"); results+=("PASS $((SECONDS - t))s")
  else
    names+=("$label"); results+=("FAIL $((SECONDS - t))s")
  fi
}

in_dir() { (cd "$1" && shift && "$@"); }

npm_install() { [ -d "$1/node_modules" ] || in_dir "$1" npm ci --no-audit --no-fund; }

# ---------------- backend ----------------
if command -v uv >/dev/null 2>&1; then
  run "backend: install"        in_dir backend uv sync --frozen
  run "backend: ruff lint"      in_dir backend uv run ruff check .
  run "backend: ruff format"    in_dir backend uv run ruff format --check .
  run "backend: mypy"           in_dir backend uv run mypy .
  run "backend: pytest"         in_dir backend uv run pytest
  run "pyright (editor types)"  uvx pyright
else
  echo "uv not found (https://docs.astral.sh/uv/); running backend checks inside Docker instead."
  backend_in_docker() {
    docker compose run --rm --no-deps -T web sh -c \
      "ruff check . && ruff format --check . && mypy . && DJANGO_SETTINGS_MODULE=faultkeeper.settings_test pytest"
  }
  run "backend: lint, types, tests (Docker)" backend_in_docker
fi

# ---------------- frontend ----------------
run "frontend: install"    npm_install frontend
run "frontend: lint"       in_dir frontend npm run lint
run "frontend: typecheck"  in_dir frontend npm run typecheck
run "frontend: tests"      in_dir frontend npm test
run "frontend: build"      in_dir frontend npm run build

# ---------------- demo storefront ----------------
run "buggy-shop: install"   npm_install demo/buggy-shop
run "buggy-shop: typecheck" in_dir demo/buggy-shop npm run typecheck
run "buggy-shop: build"     in_dir demo/buggy-shop npm run build

# ---------------- docker: smoke, end-to-end, production image ----------------
if [ "$QUICK" = 0 ]; then
  was_running=0
  curl -fs -o /dev/null --max-time 3 http://localhost:8000/api/0/health/ && was_running=1

  compose_up() {
    [ -f .env ] || cp .env.example .env
    docker compose up -d --build || return 1
    for _ in $(seq 1 180); do
      curl -fs -o /dev/null --max-time 3 http://localhost:8000/api/0/health/ && return 0
      sleep 1
    done
    docker compose logs --tail 50; return 1
  }
  e2e() {
    docker compose run --rm --no-deps -T -v "$ROOT/loadtest:/lt" web \
      python /lt/send_events.py --dsn http://79a635b512d79894d720b95fbdad5008@web:8000/3 \
      --events 300 --bugs 7 --concurrency 8 --verify --expect-exact
  }
  run "docker: stack starts and is healthy"   compose_up
  run "e2e: 300 events -> exactly 7 issues"   e2e
  run "docker: production image builds"       docker build -q -t faultkeeper:check .
  if [ "$was_running" = 0 ]; then docker compose down >/dev/null 2>&1; fi
fi

# ---------------- summary ----------------
printf '\n%-44s %s\n' "CHECK" "RESULT"
failed=0
for i in "${!names[@]}"; do
  case "${results[$i]}" in FAIL*) failed=$((failed + 1)); color='\033[1;31m' ;; *) color='\033[1;32m' ;; esac
  printf "%-44s ${color}%s\033[0m\n" "${names[$i]}" "${results[$i]}"
done
printf '\n%d checks, %d failed, %ss total\n' "${#names[@]}" "$failed" "$((SECONDS - started))"
[ "$failed" = 0 ]
