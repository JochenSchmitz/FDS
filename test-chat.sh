#!/usr/bin/env bash
# Chat-Test für das Instruct-Modell (ChatML → Chat-Completions-API).
# Aufruf: ./test-chat.sh ["Eigene Frage"] ["System-Prompt"]
# Tipp des Modell-Autors: System-Prompt in der Sprache der Frage stellen.
set -euo pipefail

API=http://localhost:8011/v1/chat/completions
MODEL=martinsu/tildeopen-30b-mu-instruct

if ! curl -sf -m 5 http://localhost:8011/health >/dev/null; then
  echo "FEHLER: Das Instruct-Modell antwortet nicht auf Port 8011." >&2
  echo "Starten mit:  docker compose --profile base down && docker compose --profile instruct up -d" >&2
  echo "(Es kann nur ein Modell gleichzeitig laufen; Laden dauert einige Minuten.)" >&2
  exit 1
fi

QUESTION=${1:-"Wie heißt die Hauptstadt von Italien?"}
SYSTEM=${2:-"Du bist ein hilfreicher Assistent. Antworte auf Deutsch."}

echo "── Frage ───────────────────────────────────────────"
echo "$QUESTION"
echo "── Antwort ─────────────────────────────────────────"
curl -sf "$API" \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c "
import json, sys
print(json.dumps({
    'model': '$MODEL',
    'messages': [
        {'role': 'system', 'content': sys.argv[2]},
        {'role': 'user', 'content': sys.argv[1]},
    ],
    'max_tokens': 400,
    'temperature': 0.7,
}))" "$QUESTION" "$SYSTEM")" | python3 -c "import json,sys; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
