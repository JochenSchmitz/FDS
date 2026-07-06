#!/usr/bin/env bash
# Schneller Funktionstest für TildeOpen-30b (Base-Modell → Completions-API).
# Aufruf: ./test-tilde.sh ["Eigener Prompt"]
set -euo pipefail

API=http://localhost:8010/v1/completions
MODEL=TildeAI/TildeOpen-30b

if ! curl -sf -m 5 http://localhost:8010/health >/dev/null; then
  echo "FEHLER: Das Base-Modell antwortet nicht auf Port 8010." >&2
  echo "Starten mit:  docker compose --profile instruct down && docker compose --profile base up -d" >&2
  echo "(Es kann nur ein Modell gleichzeitig laufen; Laden dauert einige Minuten.)" >&2
  exit 1
fi

complete() {
  local prompt=$1
  echo "── Prompt ──────────────────────────────────────────"
  echo "$prompt"
  echo "── Fortsetzung ─────────────────────────────────────"
  curl -sf "$API" \
    -H 'Content-Type: application/json' \
    -d "$(python3 -c "
import json, sys
print(json.dumps({
    'model': '$MODEL',
    'prompt': sys.argv[1],
    'max_tokens': 120,
    'temperature': 0.3,
    'repetition_penalty': 1.2,  # Empfehlung aus der Model Card
}))" "$prompt")" | python3 -c "import json,sys; print(json.load(sys.stdin)['choices'][0]['text'])"
  echo
}

if [[ $# -ge 1 ]]; then
  complete "$1"
  exit 0
fi

# Mehrsprachige Beispiel-Prompts (Stärke des Modells: europäische Sprachen)
complete "Die Hauptstadt von Lettland ist"
complete "Šodien Rīgā ir skaists laiks, tāpēc mēs nolēmām"
complete "Frage: Was ist der Unterschied zwischen Wetter und Klima?
Antwort:"
complete "Übersetze ins Estnische.
Deutsch: Guten Morgen, wie geht es dir?
Estnisch:"
