# TildeOpen-30b Test-Setup

vLLM-Container (NVIDIA NGC, ARM64/DGX Spark) mit zwei Modellen in voller BF16-Präzision:

| Profil | Modell | Port | Art |
|---|---|---|---|
| `base` | [TildeAI/TildeOpen-30b](https://huggingface.co/TildeAI/TildeOpen-30b) | 8010 | Base-Modell (Textfortsetzung) |
| `instruct` | [martinsu/tildeopen-30b-mu-instruct](https://huggingface.co/martinsu/tildeopen-30b-mu-instruct) | 8011 | Community-Fine-Tune (Chat, ChatML, 25 Sprachen) |
| `ocr` | [Qwen/Qwen3-VL-32B-Instruct-FP8](https://huggingface.co/Qwen/Qwen3-VL-32B-Instruct-FP8) | 8012 | Vision-Modell für Dokument-OCR (Scans → Text) |

**Es kann immer nur eines laufen** (je ~60 GB Gewichte; der Ollama-Systemdienst belegt zusätzlich dauerhaft ~22 GB Unified Memory).

## Dokumenten-OCR-Anwendung (DB + Weboberfläche)

Komplette Pipeline: Dokumente im Browser hochladen → OCR durch das
Vision-Modell → Verschlagwortung/Zusammenfassung/Dokumentdatum automatisch →
Ergebnisse als `.md` + `.docx` in `ergebnisse/` → Metadaten in Postgres →
Side-by-Side-Viewer (Original | OCR-Ergebnis) über OnlyOffice.

```bash
./dev-temux-start.sh   # Entwicklung: Backend (--reload) + Vite + ngrok in tmux
./dev-temux-stop.sh    # ... alles wieder stoppen
./start-app.sh         # Alternative ohne tmux/ngrok: nur lokal auf Port 8020
```

Weboberfläche: lokal **http://localhost:5175** (Vite) bzw. **http://172.31.102.13:8020**
(Backend liefert den letzten `npm run build`-Stand), extern
**https://dokumentenkonvertierung.ngrok.io** (ngrok, Bezahl-Account).

**Anmeldung:** Alle API-Endpunkte und die Oberfläche erfordern einen Login.
Die Benutzer (E-Mail + Passwort) stehen in der `.env` (`AUTH_USERS`);
die Sitzung hält 7 Tage (`AUTH_SESSION_DAYS`, HttpOnly-Cookie, signiert mit
`AUTH_SECRET`). OnlyOffice ruft Dokumente über kurzlebige, dokumentgebundene
signierte Tokens ab. Neue Benutzer: Zeile in `AUTH_USERS` ergänzen und
Backend neu starten.

Alle Zugangsdaten/Tokens liegen in `.env` (nicht im Git; Vorlage:
`.env.example`). Der OnlyOffice-Viewer bekommt seine öffentliche URL zur
Laufzeit über die lokale ngrok-API (Port 4043, in `ngrok.yml` gepinnt —
4040/4041 gehören den Agenten der Projekte wdf/vip).

Makefile-Targets: `make backend` / `frontend` / `ngrok` / `infra-up` /
`infra-down` / `quality` (ruff + pytest) / `format` / `test` / `install`.
Versionierter Commit-Helfer: `./commit.sh "Nachricht"` (pflegt `VERSION`).
Git-Remote: https://github.com/JochenSchmitz/DokumentenKonvertierung

| Komponente | Technik | Wo |
|---|---|---|
| Datenbank | Postgres 18.3 (Docker, `tildeai-db`) | Port 5435, User/DB `dokumente` |
| Backend + Worker | FastAPI/Uvicorn, SQLAlchemy, UUID7 | Port 8020, Code in `backend/` |
| Frontend | Vite + Vue 3 + TypeScript + Pinia | `frontend/` (Build wird vom Backend ausgeliefert) |
| Viewer | OnlyOffice Document Server (bestehender Container) | Port 8082, JWT-signierte Configs |
| OCR/Metadaten | Qwen3-VL-32B-FP8 (Compose-Profil `ocr`) | Port 8012 |

Frontend-Entwicklung mit Hot-Reload: `cd frontend && npm run dev`
(Port 5175, proxied `/api` zum Backend); danach `npm run build`, damit das
Backend den neuen Stand ausliefert. Originale liegen in `data/originals/`
(Dateiname = UUID), Ergebnisse in `ergebnisse/`, Volltexte seitenweise in
der Tabelle `pages`.

## Wichtig zu wissen

- **Base-Modell, kein Chat-Modell**: TildeOpen-30b ist ein Foundation-Modell ohne
  Instruction-Tuning. Es setzt Text fort, statt auf Anweisungen zu antworten.
  → `/v1/completions` verwenden, nicht `/v1/chat/completions`.
  Für Frage-Antwort-Tests Prompts als Muster formulieren (Few-Shot oder `Frage: … Antwort:`).
- **Stärke**: europäische Sprachen, besonders kleinere (Lettisch, Litauisch, Estnisch,
  Isländisch, Maltesisch, …) — gleichmäßige Tokenisierung über alle Sprachen.
- Kontext ist auf 16k begrenzt (`--max-model-len`), das Modell könnte bis 64k.
- `--gpu-memory-utilization 0.60` ist bewusst konservativ, weil der Ollama-Systemdienst
  dauerhaft ~22 GB des Unified Memory belegt.
- Geschwindigkeit: ~3–4 Tokens/s pro Anfrage (BF16, 30B, bandbreitenlimitiert auf GB10).
  Parallele Anfragen erhöhen den Gesamtdurchsatz deutlich (Batching).

## Tokenizer-Fix (wichtig!)

Die Model Card verlangt `use_fast=False` — den Slow-Tokenizer gibt es in
transformers 5.x (im vLLM-Container) aber nicht mehr. Die automatische
Konvertierung deklariert die 18 Whitespace-Tokens des Tilde-Tokenizers
(`' '`, `'\n'`, `'\t'`, …) als Spezial-Tokens und zerhackt damit jeden Prompt:
Zwischen jedem Wort landet ein Leerzeichen-Token (ID 179), das das Modell im
Training nie gesehen hat → eingestreuter Zeichenmüll in den Ausgaben.

[hf-home/fix_tokenizer.py](hf-home/fix_tokenizer.py) erzeugt deshalb pro Modell
einen korrigierten Tokenizer (Whitespace-Tokens aus `added_tokens`,
`added_tokens_decoder` und `extra_special_tokens` entfernt; echte
Spezial-Tokens wie die ChatML-Marker bleiben erhalten) und validiert ihn
gegen den originalen SentencePiece-Tokenizer. Die Compose-Datei bindet sie
per `--tokenizer` ein. Bei Bedarf neu erzeugen (in einem laufenden Container):

```bash
docker exec tildeopen-instruct-vllm python3 /hf-home/fix_tokenizer.py \
  martinsu/tildeopen-30b-mu-instruct /hf-home/tilde-instruct-tokenizer-fixed
```

## Bedienung

```bash
# Base-Modell (Completions, Port 8010)
docker compose --profile base up -d
./test-tilde.sh                     # mehrsprachige Beispiel-Prompts
./test-tilde.sh "Mans vārds ir"     # eigener Prompt
docker compose --profile base down

# Instruct-Modell (Chat, Port 8011) — vorher das andere Profil stoppen!
docker compose --profile instruct up -d
./test-chat.sh                      # Beispielfrage
./test-chat.sh "Deine Frage" "Optionaler System-Prompt"
docker compose --profile instruct down

# OCR-Modell (Vision, Port 8012) — andere Profile vorher stoppen!
docker compose --profile ocr up -d
./ocr-test.sh scans/beispiel.pdf        # Einzeltest: PDF, erste Seite
./ocr-test.sh scans/beispiel.pdf 3      # ... Seite 3
.venv/bin/python ocr-batch.py           # ALLE Dokumente aus scans/ -> ergebnisse/*.md + *.docx
docker compose --profile ocr down

docker compose logs -f              # Logs (Modell-Laden dauert einige Minuten)
```

API: OpenAI-kompatibel (kein API-Key nötig) — Base: `http://localhost:8010/v1`
(nur `/v1/completions`), Instruct: `http://localhost:8011/v1` (`/v1/chat/completions`).
Tipp des Fine-Tune-Autors: System-Prompt in der Sprache der Frage formulieren.

```bash
curl http://localhost:8010/v1/completions \
  -H 'Content-Type: application/json' \
  -d '{"model": "TildeAI/TildeOpen-30b", "prompt": "Rīga ir", "max_tokens": 50}'
```

## Verzeichnis

- `hf-home/` — Hugging-Face-Cache mit den Modellgewichten (2 × ~60 GB), wird in die Container gemountet
- `hf-home/tilde-tokenizer-fixed/`, `hf-home/tilde-instruct-tokenizer-fixed/` — korrigierte Tokenizer (siehe oben)
- `hf-home/fix_tokenizer.py` — erzeugt und validiert die korrigierten Tokenizer:
  `docker exec <container> python3 /hf-home/fix_tokenizer.py <repo> <ausgabe-dir>`
- `test-chat.sh` — Chat-Test für das Instruct-Modell
- `ocr-test.sh` — Einzelseiten-OCR-Test; `ocr-batch.py` — Batch-OCR für alle Scans
- `scans/` — Eingangsordner für zu lesende Dokumente; `ergebnisse/` — OCR-Ausgabe (.md + .docx)
- `.venv/` — Python 3.14.3 (via uv) mit pypandoc-binary für die Word-Konvertierung:
  `uv venv --python 3.14.3 .venv && uv pip install --python .venv/bin/python pypandoc-binary`
- `docker-compose.yml` — Container-Definition
- `test-tilde.sh` — Schnelltest-Skript
