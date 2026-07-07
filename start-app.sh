#!/usr/bin/env bash
# Startet den kompletten FES Dokumenten Service (FDS):
# Postgres + OCR-Modell (Docker) und das FastAPI-Backend (Vordergrund).
# Beenden mit Strg+C (die Container laufen weiter).
set -euo pipefail
cd "$(dirname "$0")"

docker compose up -d db
docker compose --profile ocr up -d

echo "Warte auf OCR-Modell (erster Start dauert einige Minuten) ..."
until curl -sf -m 2 http://localhost:8012/health >/dev/null; do sleep 5; done
echo "OCR-Modell bereit."

echo "Weboberfläche: http://172.31.102.13:8020"
exec .venv/bin/python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8020
