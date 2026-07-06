#!/usr/bin/env python3
"""OCR-Batch: alle Dokumente aus scans/ -> Markdown + Word in ergebnisse/.

Aufruf:  .venv/bin/python ocr-batch.py
Verarbeitet PDF/PNG/JPG/TIFF. Pro Dokument entstehen ergebnisse/<name>.md
und <name>.docx mit einem Abschnitt je Seite. Bereits vorhandene Dateien
werden übersprungen (die .md löschen, um neu zu lesen; nur die .docx
löschen, um sie aus der .md neu zu erzeugen).
Benötigt poppler (pdftoppm) und pypandoc-binary (im .venv installiert).
"""
import base64
import json
import re
import subprocess
import sys
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pypandoc

API = 'http://localhost:8012/v1/chat/completions'
MODEL = 'Qwen/Qwen3-VL-32B-Instruct-FP8'
SCANS = Path(__file__).parent / 'scans'
OUT = Path(__file__).parent / 'ergebnisse'
PARALLEL = 4       # Seiten gleichzeitig (vLLM batcht intern)
DPI = 200

PROMPT = (
    'Extrahiere den vollständigen Text dieser gescannten Dokumentseite. '
    'Gib den Inhalt als sauberes Markdown wieder: Überschriften als '
    'Überschriften, Tabellen als Markdown-Tabellen, Listen als Listen. '
    'Gib ausschließlich den Dokumentinhalt aus, keine Kommentare. '
    'Unleserliche Stellen markiere mit [unleserlich]. '
    'Logos und Grafiken nicht als Bild-Links einbetten, sondern kurz in '
    'eckigen Klammern beschreiben, z.B. [Logo: SwS].'
)


def ocr_image(png: Path) -> str:
    b64 = base64.b64encode(png.read_bytes()).decode()
    body = json.dumps({
        'model': MODEL,
        'messages': [{'role': 'user', 'content': [
            {'type': 'image_url',
             'image_url': {'url': f'data:image/png;base64,{b64}'}},
            {'type': 'text', 'text': PROMPT},
        ]}],
        'max_tokens': 8000,
        'temperature': 0,
    }).encode()
    req = urllib.request.Request(
        API, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.load(r)['choices'][0]['message']['content']


def page_count(pdf: Path) -> int:
    info = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True)
    for line in info.stdout.splitlines():
        if line.startswith('Pages:'):
            return int(line.split()[-1])
    raise RuntimeError(f'Seitenzahl nicht ermittelbar: {pdf}')


def render_page(pdf: Path, page: int, tmpdir: str) -> Path:
    out = Path(tmpdir) / f'seite-{page:03d}'
    subprocess.run(
        ['pdftoppm', '-png', '-r', str(DPI), '-f', str(page), '-l', str(page),
         '-singlefile', str(pdf), str(out)],
        check=True)
    return out.with_suffix('.png')


def process(doc: Path) -> None:
    target_md = OUT / f'{doc.stem}.md'
    target_docx = OUT / f'{doc.stem}.docx'

    if target_md.exists():
        print(f'übersprungen (existiert): {target_md.name}')
    else:
        print(f'verarbeite: {doc.name}')
        with tempfile.TemporaryDirectory() as tmpdir:
            if doc.suffix.lower() == '.pdf':
                pages = [render_page(doc, p, tmpdir)
                         for p in range(1, page_count(doc) + 1)]
            else:
                pages = [doc]

            with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
                texts = list(pool.map(ocr_image, pages))

        parts = [f'# {doc.name}\n']
        for i, text in enumerate(texts, 1):
            parts.append(f'\n---\n\n## Seite {i}\n\n{text}\n')
        target_md.write_text(''.join(parts))
        print(f'  -> {target_md} ({len(texts)} Seiten)')

    if not target_docx.exists():
        # Bild-Links (z.B. vom Modell erfundene Logo-Platzhalter-URLs) in
        # Textbeschreibungen umwandeln — pandoc würde sie sonst über das
        # Netz abrufen wollen; die Konvertierung soll strikt offline sein.
        md_text = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'[Grafik: \1]',
                         target_md.read_text())
        pypandoc.convert_text(md_text, 'docx', format='markdown',
                              outputfile=str(target_docx))
        print(f'  -> {target_docx}')


def main() -> int:
    OUT.mkdir(exist_ok=True)
    docs = sorted(p for p in SCANS.iterdir()
                  if p.suffix.lower() in ('.pdf', '.png', '.jpg', '.jpeg', '.tif', '.tiff'))
    if not docs:
        print(f'Keine Dokumente in {SCANS} gefunden.', file=sys.stderr)
        return 1
    try:
        urllib.request.urlopen('http://localhost:8012/health', timeout=5)
    except OSError:
        print('FEHLER: Das OCR-Modell antwortet nicht auf Port 8012.\n'
              'Starten mit:  docker compose --profile ocr up -d', file=sys.stderr)
        return 1
    for doc in docs:
        process(doc)
    print('fertig.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
