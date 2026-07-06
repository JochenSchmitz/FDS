"""OnlyOffice-Integration.

Links: Original-PDF als schlanker Viewer (Frontend nutzt type=embedded).
Rechts: OCR-Ergebnis (.docx) im Bearbeitungsmodus — OnlyOffice speichert
Änderungen über den Callback-Endpoint zurück in die Ergebnisdatei.
Alle Configs sind JWT-signiert (Secret des Document Servers).
"""

import logging
import uuid

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request

from .. import auth, config
from ..db import SessionDep
from .documents import _get_document

router = APIRouter(prefix='/api/onlyoffice', tags=['onlyoffice'])
log = logging.getLogger('onlyoffice')


@router.get('/{doc_id}/{side}')
def viewer_config(doc_id: uuid.UUID, side: str, db: SessionDep, user: auth.UserDep):
    doc = _get_document(doc_id, db)
    # OnlyOffice ruft die Datei serverseitig ohne Sitzungs-Cookie ab —
    # deshalb bekommt die URL ein signiertes, dokumentgebundenes Token.
    file_token = auth.create_file_token(doc.id)

    if side == 'original':
        if not doc.mime.startswith('application/pdf'):
            raise HTTPException(
                409, 'Original ist ein Bild — direkt im Browser anzeigen'
            )
        file_type, document_type = 'pdf', 'pdf'
        url = (
            f'{config.PUBLIC_BASE_URL}/api/documents/{doc.id}/file/original'
            f'?token={file_token}'
        )
        title = doc.filename
        mode = 'view'
        stamp = int(doc.processed_at.timestamp()) if doc.processed_at else 0
    elif side == 'result':
        if not doc.result_stem:
            raise HTTPException(409, 'Dokument ist noch nicht verarbeitet')
        file_type, document_type = 'docx', 'word'
        url = (
            f'{config.PUBLIC_BASE_URL}/api/documents/{doc.id}/file/docx'
            f'?token={file_token}'
        )
        title = f'{doc.filename} (OCR-Ergebnis)'
        mode = 'edit'
        # key muss sich bei jeder gespeicherten Änderung ändern, sonst
        # liefert der Document Server eine gecachte alte Version aus
        docx = config.RESULTS_DIR / f'{doc.result_stem}.docx'
        stamp = int(docx.stat().st_mtime) if docx.exists() else 0
    else:
        raise HTTPException(404, 'side muss original oder result sein')

    payload = {
        'document': {
            'fileType': file_type,
            'key': f'{doc.id.hex[:16]}-{side}-{stamp}',
            'title': title,
            'url': url,
            'permissions': {
                'edit': mode == 'edit',
                'download': True,
                'print': True,
            },
        },
        'documentType': document_type,
        'editorConfig': {
            'mode': mode,
            'lang': 'de',
            'user': {'id': user, 'name': user},
            'customization': {
                'compactHeader': True,
                'hideRightMenu': True,
                'autosave': True,
            },
        },
    }
    if mode == 'edit':
        payload['editorConfig']['callbackUrl'] = (
            f'{config.PUBLIC_BASE_URL}/api/onlyoffice/callback/{doc.id}'
        )
    payload['token'] = jwt.encode(
        payload, config.ONLYOFFICE_JWT_SECRET, algorithm='HS256'
    )
    return payload


def _callback_data(body: dict, request: Request) -> dict:
    """Callback-Daten JWT-verifiziert extrahieren.

    Der Document Server schickt (je nach Konfiguration) das JWT im Body
    ('token') und/oder im Authorization-Header; die Nutzdaten stecken im
    Token-Payload (ggf. unter 'payload').
    """
    token = body.get('token')
    if not token:
        bearer = request.headers.get('Authorization', '')
        token = bearer.removeprefix('Bearer ').strip() or None
    if not token:
        raise HTTPException(403, 'OnlyOffice-Callback ohne Token')
    try:
        data = jwt.decode(token, config.ONLYOFFICE_JWT_SECRET, algorithms=['HS256'])
    except jwt.PyJWTError as exc:
        raise HTTPException(403, f'OnlyOffice-Token ungültig: {exc}') from exc
    return data.get('payload', data)


@router.post('/callback/{doc_id}')
async def onlyoffice_callback(doc_id: uuid.UUID, request: Request, db: SessionDep):
    """Speichert von OnlyOffice bearbeitete Dokumente zurück.

    Status 2 = Bearbeitung beendet, speichern; 6 = Zwischenspeichern
    (Force-Save/Autosave). Antwort {'error': 0} ist Pflicht, sonst
    meldet der Editor einen Speicherfehler.
    """
    doc = _get_document(doc_id, db)
    body = await request.json()
    data = _callback_data(body, request)
    status = data.get('status')

    if status in (2, 6):
        url = data.get('url')
        if not url or not doc.result_stem:
            raise HTTPException(400, 'Callback ohne Download-URL')
        target = config.RESULTS_DIR / f'{doc.result_stem}.docx'
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=120)
            resp.raise_for_status()
            target.write_bytes(resp.content)
        log.info(
            '%s: bearbeitete .docx gespeichert (%d Bytes, Status %s)',
            doc.filename,
            len(resp.content),
            status,
        )

    return {'error': 0}
