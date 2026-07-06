#!/usr/bin/env bash
set -euo pipefail

SESSION_NAME="${SESSION_NAME:-dokkonv-dev}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

stop_matching_processes() {
  local signal="$1"

  # Muster bewusst projektspezifisch halten — auf dem Server laufen
  # weitere uvicorn/vite/ngrok-Prozesse anderer Projekte.
  pkill -"${signal}" -f "uvicorn backend.app.main:app .*--port 8020" 2>/dev/null || true
  pkill -"${signal}" -f "${PROJECT_ROOT}/frontend/node_modules/.*vite" 2>/dev/null || true
  pkill -"${signal}" -f "ngrok start --all" 2>/dev/null || true
}

stop_dev_ports() {
  fuser -k 8020/tcp 2>/dev/null || true
  fuser -k 5175/tcp 2>/dev/null || true
}

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux ist nicht installiert oder nicht im PATH." >&2
  exit 1
fi

if tmux has-session -t "${SESSION_NAME}" 2>/dev/null; then
  tmux send-keys -t "${SESSION_NAME}" C-c 2>/dev/null || true
  sleep 1
  tmux kill-session -t "${SESSION_NAME}" 2>/dev/null || true
  echo "tmux-Session ${SESSION_NAME} wurde beendet."
else
  echo "tmux-Session ${SESSION_NAME} läuft nicht."
fi

stop_matching_processes TERM
sleep 1
stop_dev_ports
stop_matching_processes KILL

if command -v docker >/dev/null 2>&1; then
  docker compose -f "${PROJECT_ROOT}/docker-compose.yml" --profile ocr stop >/dev/null 2>&1 || true
  echo "Docker-Container tildeai-db und qwen-ocr-vllm wurden gestoppt."
fi
