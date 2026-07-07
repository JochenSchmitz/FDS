"""Upload-Tests: Duplikat-Erkennung (SHA-256) und ZIP-Entpacken.

Nutzt die Test-DB aus conftest.py; die Original-Dateien landen im
echten data/originals und werden am Testende per DELETE wieder
entfernt. Die Inhalte sind pro Lauf zufällig, damit Reste eines
abgebrochenen Laufs keine falschen Duplikat-Treffer erzeugen.
"""

import io
import os
import zipfile

from fastapi.testclient import TestClient

from backend.app.main import app


def _login(client: TestClient) -> None:
    resp = client.post(
        '/api/auth/login',
        json={'email': 'test@example.org', 'password': 'test-passwort'},
    )
    assert resp.status_code == 200


def test_duplikat_wird_abgelehnt():
    with TestClient(app) as client:
        _login(client)
        payload = b'%PDF-testinhalt-' + os.urandom(16).hex().encode()

        resp = client.post(
            '/api/documents',
            files=[('files', ('bericht.pdf', payload, 'application/pdf'))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['created']) == 1
        assert data['skipped'] == []
        doc_id = data['created'][0]['id']

        try:
            # Gleicher Inhalt, anderer Name -> Duplikat, kurzer Hinweis
            resp = client.post(
                '/api/documents',
                files=[('files', ('kopie.pdf', payload, 'application/pdf'))],
            )
            data = resp.json()
            assert data['created'] == []
            assert len(data['skipped']) == 1
            assert 'bereits vorhanden' in data['skipped'][0]['reason']
            assert 'bericht.pdf' in data['skipped'][0]['reason']
        finally:
            assert client.delete(f'/api/documents/{doc_id}').status_code == 204


def test_zip_wird_entpackt_ordner_werden_tags():
    with TestClient(app) as client:
        _login(client)
        pdf = b'%PDF-zipinhalt-' + os.urandom(16).hex().encode()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as zf:
            zf.writestr('Projekt A/Berichte/scan.pdf', pdf)
            zf.writestr('Projekt A/notiz.txt', b'kein unterstuetzter Typ')
            zf.writestr('Projekt A/Berichte/nochmal.pdf', pdf)  # Duplikat im ZIP

        resp = client.post(
            '/api/documents',
            files=[('files', ('archiv.zip', buf.getvalue(), 'application/zip'))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['created']) == 1
        doc = data['created'][0]
        try:
            assert doc['filename'] == 'scan.pdf'
            # Ordnerstruktur im Archiv -> Schlagworte, sofort sichtbar
            assert doc['tags'] == ['Projekt A', 'Berichte']

            reasons = {s['filename']: s['reason'] for s in data['skipped']}
            assert 'nicht unterstützt' in reasons['Projekt A/notiz.txt']
            assert (
                'mehrfach im selben Upload' in reasons['Projekt A/Berichte/nochmal.pdf']
            )
        finally:
            assert client.delete(f'/api/documents/{doc["id"]}').status_code == 204


def test_unbekannter_typ_wird_abgelehnt():
    with TestClient(app) as client:
        _login(client)
        resp = client.post(
            '/api/documents',
            files=[('files', ('tabelle.xlsx', b'x', 'application/octet-stream'))],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['created'] == []
        assert 'nicht unterstützt' in data['skipped'][0]['reason']


def test_defektes_zip_wird_per_fallback_gerettet():
    """OneDrive-Symptom: zentrales Verzeichnis fehlt/defekt — zipfile
    lehnt ab, der stream-unzip-Fallback rettet die Dateien trotzdem."""
    with TestClient(app) as client:
        _login(client)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                'Akte/eins.pdf', b'%PDF-fallback-' + os.urandom(16).hex().encode()
            )
            zf.writestr(
                'Akte/zwei.pdf', b'%PDF-fallback-' + os.urandom(16).hex().encode()
            )
        data_bytes = buf.getvalue()
        kaputt = data_bytes[: data_bytes.index(b'PK\x01\x02')]

        resp = client.post(
            '/api/documents',
            files=[('files', ('onedrive.zip', kaputt, 'application/zip'))],
        )
        assert resp.status_code == 200
        data = resp.json()
        try:
            assert [d['filename'] for d in data['created']] == ['eins.pdf', 'zwei.pdf']
            assert all(d['tags'] == ['Akte'] for d in data['created'])
            # Hinweis, dass das Archiv defekt war und wie viel gerettet wurde
            assert len(data['skipped']) == 1
            assert 'nach 2 geretteten Dateien' in data['skipped'][0]['reason']
        finally:
            for d in data['created']:
                assert client.delete(f'/api/documents/{d["id"]}').status_code == 204


def test_leeres_und_falsches_zip_bekommen_diagnose():
    with TestClient(app) as client:
        _login(client)
        resp = client.post(
            '/api/documents',
            files=[('files', ('platzhalter.zip', b'', 'application/zip'))],
        )
        assert '0 Bytes' in resp.json()['skipped'][0]['reason']

        resp = client.post(
            '/api/documents',
            files=[('files', ('seite.zip', b'<html>Fehler</html>', 'application/zip'))],
        )
        assert 'keine ZIP-Signatur' in resp.json()['skipped'][0]['reason']
