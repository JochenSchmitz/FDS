import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, ocr
from .auth import UserDep
from .db import Base, engine
from .routers import auth, documents, onlyoffice

logging.basicConfig(
    level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)


def _init_search(connection) -> None:
    """Trigram-Suche: Extension + GIN-Indizes für ILIKE '%...%'-Suchen."""
    from sqlalchemy import text

    connection.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))
    for ddl in (
        # Alte, zeichengenaue Indizes durch Expression-Indizes auf dem
        # whitespace-bereinigten Text ersetzen: die Suche entfernt in
        # Query UND Text alle Leerzeichen ("ad blue" findet "AdBlue",
        # "Gewähr Leistung" findet "Gewährleistung").
        'DROP INDEX IF EXISTS ix_documents_filename_trgm',
        'DROP INDEX IF EXISTS ix_documents_summary_trgm',
        'DROP INDEX IF EXISTS ix_pages_content_trgm',
        'CREATE INDEX IF NOT EXISTS ix_documents_filename_trgm_ws '
        'ON documents USING gin '
        "((regexp_replace(filename, '\\s', '', 'g')) gin_trgm_ops)",
        'CREATE INDEX IF NOT EXISTS ix_documents_summary_trgm_ws '
        'ON documents USING gin '
        "((regexp_replace(summary, '\\s', '', 'g')) gin_trgm_ops)",
        'CREATE INDEX IF NOT EXISTS ix_pages_content_trgm_ws '
        'ON pages USING gin '
        "((regexp_replace(content_md, '\\s', '', 'g')) gin_trgm_ops)",
    ):
        connection.execute(text(ddl))
    connection.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ORIGINALS_DIR.mkdir(parents=True, exist_ok=True)
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
    with engine.connect() as connection:
        _init_search(connection)
    from .worker import worker_loop

    task = asyncio.create_task(worker_loop())
    yield
    task.cancel()


app = FastAPI(title='Dokumente-OCR', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # internes LAN-Tool; bei Bedarf einschränken
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(onlyoffice.router)


async def _onlyoffice_public_url() -> str:
    """OnlyOffice-URL für den Browser.

    Läuft ein ngrok-Tunnel auf Port 8082, dessen (dynamische) HTTPS-URL
    zurückgeben — nötig, wenn die Seite selbst über ngrok/HTTPS läuft,
    weil der Browser das OnlyOffice-Script sonst nicht laden darf
    (Mixed Content). Fallback: die LAN-URL aus der Konfiguration.
    """
    import os

    import httpx

    ngrok_api = os.environ.get('NGROK_API_URL', 'http://localhost:4043')
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f'{ngrok_api}/api/tunnels', timeout=1)
            for tunnel in resp.json().get('tunnels', []):
                if tunnel.get('config', {}).get('addr', '').endswith(':8082'):
                    return tunnel['public_url']
    except Exception:  # noqa: BLE001
        pass
    return config.ONLYOFFICE_URL


@app.get('/api/config')
async def frontend_config(user: UserDep):
    return {
        'onlyofficeUrl': await _onlyoffice_public_url(),
        'apiBaseUrl': config.PUBLIC_BASE_URL,
        'ocrModelUp': await ocr.is_model_up(),
    }


# Gebautes Frontend (frontend/dist) direkt mit ausliefern, falls vorhanden
if config.FRONTEND_DIST.is_dir():
    app.mount(
        '/', StaticFiles(directory=config.FRONTEND_DIST, html=True), name='frontend'
    )
