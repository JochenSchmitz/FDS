"""Anmeldung mit Benutzer/Passwort aus der .env, Sitzung als signierter
JWT im HttpOnly-Cookie (Laufzeit: AUTH_SESSION_DAYS, Standard 7 Tage).

Für OnlyOffice gibt es signierte Datei-Tokens: der Document Server ruft
die Dokumente serverseitig ohne Cookie ab und bekommt deshalb eine URL
mit ?token=..., das nur für genau ein Dokument gilt.
"""

import datetime
import secrets
import uuid
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, HTTPException

from . import config

SESSION_COOKIE = 'session'
_FILE_TOKEN_HOURS = 24


def verify_credentials(email: str, password: str) -> bool:
    expected = config.AUTH_USERS.get(email.strip().lower())
    return expected is not None and secrets.compare_digest(expected, password)


def _expiry(**delta) -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC) + datetime.timedelta(**delta)


def create_session_token(email: str) -> str:
    payload = {'sub': email, 'exp': _expiry(days=config.AUTH_SESSION_DAYS)}
    return jwt.encode(payload, config.AUTH_SECRET, algorithm='HS256')


def session_max_age() -> int:
    return config.AUTH_SESSION_DAYS * 86400


def user_from_session(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return jwt.decode(token, config.AUTH_SECRET, algorithms=['HS256'])['sub']
    except jwt.PyJWTError:
        return None


async def require_user(
    session: Annotated[str | None, Cookie()] = None,
) -> str:
    user = user_from_session(session)
    if user is None:
        raise HTTPException(401, 'Nicht angemeldet oder Sitzung abgelaufen')
    return user


UserDep = Annotated[str, Depends(require_user)]


def create_file_token(doc_id: uuid.UUID) -> str:
    payload = {'doc': str(doc_id), 'exp': _expiry(hours=_FILE_TOKEN_HOURS)}
    return jwt.encode(payload, config.AUTH_SECRET, algorithm='HS256')


def check_file_access(
    doc_id: uuid.UUID, session: str | None, token: str | None
) -> None:
    """Dateizugriff: angemeldeter Benutzer ODER passendes Datei-Token."""
    if user_from_session(session) is not None:
        return
    if token:
        try:
            payload = jwt.decode(token, config.AUTH_SECRET, algorithms=['HS256'])
            if payload.get('doc') == str(doc_id):
                return
        except jwt.PyJWTError:
            pass
    raise HTTPException(401, 'Nicht angemeldet oder Sitzung abgelaufen')
