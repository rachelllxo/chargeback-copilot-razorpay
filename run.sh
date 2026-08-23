#!/usr/bin/env bash
# Chargeback Copilot — one-command local run.
#
#   ./run.sh            → builds everything and serves on http://localhost:8080
#   PORT=3000 ./run.sh  → serves on a different port
#
# Starts a single process that serves both the application and its API,
# which is the same layout used in production.

set -euo pipefail

cd "$(dirname "$0")"
PORT="${PORT:-8080}"

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
die() { printf '\n\033[31mError: %s\033[0m\n' "$1" >&2; exit 1; }

command -v python3 >/dev/null || die "python3 is required (https://python.org/downloads)"
command -v node    >/dev/null || die "node 20+ is required (https://nodejs.org)"

step "Python environment"
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -r backend/requirements.txt
echo "dependencies installed"

step "Building the application"
cd frontend
if [ -f package-lock.json ]; then
  npm ci --silent
else
  npm install --silent
fi
npm run build
cd ..

step "Starting Chargeback Copilot"
cat <<BANNER

  Open  ->  http://localhost:${PORT}

  Demo environment, synthetic data. Press Ctrl+C to stop.

BANNER

exec ./.venv/bin/python -m uvicorn app.main:app \
  --app-dir backend --host 127.0.0.1 --port "${PORT}"
