"""Smoke-Test: App startet, Kern-Endpunkte antworten.

Voraussetzung: die Postgres aus docker-compose läuft (Port 5435).
"""

from fastapi.testclient import TestClient

from backend.app.main import app


def test_config_und_dokumentliste():
    with TestClient(app) as client:
        resp = client.get('/api/config')
        assert resp.status_code == 200
        data = resp.json()
        assert 'onlyofficeUrl' in data
        assert 'apiBaseUrl' in data

        resp = client.get('/api/documents')
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
