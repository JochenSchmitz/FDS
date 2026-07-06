from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from .. import auth

router = APIRouter(prefix='/api/auth', tags=['auth'])


class LoginIn(BaseModel):
    email: str
    password: str


@router.post('/login')
def login(data: LoginIn, response: Response):
    if not auth.verify_credentials(data.email, data.password):
        raise HTTPException(401, 'E-Mail oder Passwort falsch')
    email = data.email.strip().lower()
    response.set_cookie(
        auth.SESSION_COOKIE,
        auth.create_session_token(email),
        max_age=auth.session_max_age(),
        httponly=True,
        samesite='lax',
        path='/',
    )
    return {'email': email}


@router.post('/logout')
def logout(response: Response):
    response.delete_cookie(auth.SESSION_COOKIE, path='/')
    return {'ok': True}


@router.get('/me')
def me(user: Annotated[str, Depends(auth.require_user)]):
    return {'email': user}
