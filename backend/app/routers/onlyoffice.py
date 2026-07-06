"""OnlyOffice-Viewer-Konfigurationen (JWT-signiert, Modus: nur ansehen)."""

import uuid

import jwt
from fastapi import APIRouter, HTTPException

from .. import auth, config
from ..db import SessionDep
from .documents import _get_document

router = APIRouter(prefix='/api/onlyoffice', tags=['onlyoffice'])


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
    elif side == 'result':
        if not doc.result_stem:
            raise HTTPException(409, 'Dokument ist noch nicht verarbeitet')
        file_type, document_type = 'docx', 'word'
        url = (
            f'{config.PUBLIC_BASE_URL}/api/documents/{doc.id}/file/docx'
            f'?token={file_token}'
        )
        title = f'{doc.filename} (OCR-Ergebnis)'
    else:
        raise HTTPException(404, 'side muss original oder result sein')

    # key: OnlyOffice cached pro key — bei Neuverarbeitung ändert er sich
    stamp = doc.processed_at.timestamp() if doc.processed_at else 0
    payload = {
        'document': {
            'fileType': file_type,
            'key': f'{doc.id.hex[:16]}-{side}-{int(stamp)}',
            'title': title,
            'url': url,
            'permissions': {'edit': False, 'download': True, 'print': True},
        },
        'documentType': document_type,
        'editorConfig': {
            'mode': 'view',
            'lang': 'de',
            'customization': {
                'compactHeader': True,
                'hideRightMenu': True,
                'toolbarNoTabs': True,
            },
        },
    }
    payload['token'] = jwt.encode(
        payload, config.ONLYOFFICE_JWT_SECRET, algorithm='HS256'
    )
    return payload
