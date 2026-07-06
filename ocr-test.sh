#!/usr/bin/env bash
# OCR-Test: gescannte Seite (Bild oder PDF) -> Text/Markdown.
# Aufruf: ./ocr-test.sh <datei.pdf|.png|.jpg|.tiff> [seitennummer]
# PDF-Seiten werden mit poppler (pdftoppm) in 200-dpi-PNG gewandelt.
set -euo pipefail

API=http://localhost:8012/v1/chat/completions
MODEL=Qwen/Qwen3-VL-32B-Instruct-FP8

if [[ $# -lt 1 ]]; then
  echo "Aufruf: $0 <datei.pdf|.png|.jpg> [seitennummer]" >&2
  exit 1
fi
FILE=$1
PAGE=${2:-1}

if ! curl -sf -m 5 http://localhost:8012/health >/dev/null; then
  echo "FEHLER: Das OCR-Modell antwortet nicht auf Port 8012." >&2
  echo "Starten mit:  docker compose --profile instruct down && docker compose --profile ocr up -d" >&2
  echo "(Es kann nur ein Modell gleichzeitig laufen; Laden dauert einige Minuten.)" >&2
  exit 1
fi

# PDF -> PNG der gewünschten Seite
IMG=$FILE
if [[ ${FILE,,} == *.pdf ]]; then
  IMG=$(mktemp --suffix=.png)
  trap 'rm -f "$IMG"' EXIT
  pdftoppm -png -r 200 -f "$PAGE" -l "$PAGE" -singlefile "$FILE" "${IMG%.png}"
fi

PROMPT='Extrahiere den vollständigen Text dieser gescannten Dokumentseite.
Gib den Inhalt als sauberes Markdown wieder: Überschriften als Überschriften,
Tabellen als Markdown-Tabellen, Listen als Listen. Gib ausschließlich den
Dokumentinhalt aus, keine Kommentare. Unleserliche Stellen markiere mit [unleserlich].'

python3 - "$IMG" "$PROMPT" <<'EOF'
import base64, json, mimetypes, sys
img, prompt = sys.argv[1], sys.argv[2]
mime = mimetypes.guess_type(img)[0] or 'image/png'
b64 = base64.b64encode(open(img, 'rb').read()).decode()
json.dump({
    'model': 'Qwen/Qwen3-VL-32B-Instruct-FP8',
    'messages': [{'role': 'user', 'content': [
        {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{b64}'}},
        {'type': 'text', 'text': prompt},
    ]}],
    'max_tokens': 8000,
    'temperature': 0,
}, open('/tmp/ocr-request.json', 'w'))
EOF

curl -sf "$API" -H 'Content-Type: application/json' \
  --data @/tmp/ocr-request.json \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
