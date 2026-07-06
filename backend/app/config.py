"""Zentrale Konfiguration — alles per Umgebungsvariable übersteuerbar."""

import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]

# Server-IP, unter der Browser UND OnlyOffice-Container uns erreichen
PUBLIC_HOST = os.environ.get('PUBLIC_HOST', '172.31.102.13')
BACKEND_PORT = int(os.environ.get('BACKEND_PORT', '8020'))
PUBLIC_BASE_URL = os.environ.get(
    'PUBLIC_BASE_URL', f'http://{PUBLIC_HOST}:{BACKEND_PORT}'
)

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql+psycopg://dokumente:dokumente-dev@localhost:5435/dokumente',
)

VLLM_URL = os.environ.get('VLLM_URL', 'http://localhost:8012/v1')
VLLM_MODEL = os.environ.get('VLLM_MODEL', 'Qwen/Qwen3-VL-32B-Instruct-FP8')

ONLYOFFICE_URL = os.environ.get('ONLYOFFICE_URL', f'http://{PUBLIC_HOST}:8082')
ONLYOFFICE_JWT_SECRET = os.environ.get(
    'ONLYOFFICE_JWT_SECRET', 'dev-onlyoffice-secret-change-me-32-bytes'
)

ORIGINALS_DIR = PROJECT_DIR / 'data' / 'originals'
RESULTS_DIR = PROJECT_DIR / 'ergebnisse'
FRONTEND_DIST = PROJECT_DIR / 'frontend' / 'dist'

OCR_PARALLEL = int(os.environ.get('OCR_PARALLEL', '4'))
OCR_DPI = int(os.environ.get('OCR_DPI', '200'))

OCR_PROMPT = (
    'Extrahiere den vollständigen Text dieser gescannten Dokumentseite. '
    'Gib den Inhalt als sauberes Markdown wieder: Überschriften als '
    'Überschriften, Tabellen als Markdown-Tabellen, Listen als Listen. '
    'Gib ausschließlich den Dokumentinhalt aus, keine Kommentare. '
    'Unleserliche Stellen markiere mit [unleserlich]. '
    'Logos und Grafiken nicht als Bild-Links einbetten, sondern kurz in '
    'eckigen Klammern beschreiben, z.B. [Logo: SwS].'
)

METADATA_PROMPT = (
    'Du bekommst den extrahierten Text eines gescannten Dokuments. '
    'Erstelle Metadaten dafür und antworte AUSSCHLIESSLICH mit einem '
    'JSON-Objekt in genau dieser Form, ohne Markdown-Codeblock:\n'
    '{"tags": ["5 bis 10 deutsche Schlagworte"], '
    '"summary": "Zusammenfassung in 2-3 Sätzen", '
    '"doc_date": "JJJJ-MM-TT oder null, falls kein Dokumentdatum erkennbar"}\n\n'
    'Dokumenttext:\n'
)
