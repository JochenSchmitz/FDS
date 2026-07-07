#!/usr/bin/env bash
set -euo pipefail

SESSION_NAME="${SESSION_NAME:-fds-dev}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_BIN_DIR="${NODE_BIN_DIR:-$HOME/.local/bin}"

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux ist nicht installiert oder nicht im PATH." >&2
  exit 1
fi

if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
  echo "tmux-Session ${SESSION_NAME} läuft bereits. Bitte zuerst ./dev-temux-stop.sh ausführen." >&2
  exit 1
fi

if [[ ! -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  echo "Python-Venv fehlt: ${PROJECT_ROOT}/.venv/bin/python (make install)" >&2
  exit 1
fi

if [[ ! -f "${PROJECT_ROOT}/frontend/package.json" ]]; then
  echo "Frontend package.json fehlt: ${PROJECT_ROOT}/frontend/package.json" >&2
  exit 1
fi

if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
  echo ".env fehlt — Vorlage: .env.example" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker ist nicht installiert oder nicht im PATH." >&2
  exit 1
fi

# Infrastruktur (Postgres + OCR-Modell) als Docker-Container starten.
docker compose -f "${PROJECT_ROOT}/docker-compose.yml" up -d db
docker compose -f "${PROJECT_ROOT}/docker-compose.yml" --profile ocr up -d

if [[ -d "${NODE_BIN_DIR}" ]]; then
  DEV_PATH="${NODE_BIN_DIR}:$PATH"
else
  DEV_PATH="$PATH"
fi

tmux new-session \
  -d \
  -s "${SESSION_NAME}" \
  -n backend \
  -c "${PROJECT_ROOT}" \
  "export PATH='${DEV_PATH}'; make backend"

tmux new-window \
  -t "${SESSION_NAME}" \
  -n frontend \
  -c "${PROJECT_ROOT}" \
  "export PATH='${DEV_PATH}'; make frontend"

tmux new-window \
  -t "${SESSION_NAME}" \
  -n ngrok \
  -c "${PROJECT_ROOT}" \
  "export PATH='${DEV_PATH}'; make ngrok"

echo "Backend, Frontend und ngrok-Tunnel laufen in tmux-Session ${SESSION_NAME}."
echo "Postgres + OCR-Modell laufen als Docker-Container (fds-db, qwen-ocr-vllm)."
echo "  Lokal:   http://localhost:5175"
echo "  Extern:  https://fds.ngrok.app"
echo "Anzeigen: tmux attach -t ${SESSION_NAME}"
