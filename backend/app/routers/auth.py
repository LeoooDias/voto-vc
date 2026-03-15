import urllib.parse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.core.security import criar_token, hash_senha, verificar_senha
from app.database import get_db
from app.models.base import ProvedorAuth
from app.models.usuario import Usuario

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def _is_secure() -> bool:
    return settings.frontend_url.startswith("https")


def _set_auth_cookie(response: RedirectResponse, token: str) -> None:
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=_is_secure(),
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


# --- Email/senha ---


class RegistrarRequest(BaseModel):
    email: EmailStr
    senha: str
    nome: str | None = None
    uf: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


@router.post("/registrar")
@limiter.limit(settings.rate_limit_auth)
async def registrar(request: Request, body: RegistrarRequest, db: AsyncSession = Depends(get_db)):
    existente = await db.execute(select(Usuario).where(Usuario.email == body.email))
    if existente.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    usuario = Usuario(
        email=body.email,
        senha_hash=hash_senha(body.senha),
        nome=body.nome,
        uf=body.uf,
        anonimo=False,
        provedor_auth=ProvedorAuth.EMAIL,
    )
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    token = criar_token(str(usuario.id))
    return {"token": token, "usuario_id": str(usuario.id)}


@router.post("/login")
@limiter.limit(settings.rate_limit_auth)
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.email == body.email))
    usuario = result.scalar_one_or_none()
    if not usuario or not usuario.senha_hash or not verificar_senha(body.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = criar_token(str(usuario.id))
    return {"token": token, "usuario_id": str(usuario.id)}


# --- Google OAuth ---


@router.get("/google/login")
async def google_login():
    params = urllib.parse.urlencode(
        {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
        }
    )
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{params}")


@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Falha ao autenticar com Google")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Token do Google inválido")

    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if userinfo_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Falha ao obter dados do Google")

    userinfo = userinfo_resp.json()
    google_id = userinfo["id"]
    email = userinfo.get("email")
    nome = userinfo.get("name")

    result = await db.execute(
        select(Usuario).where(
            Usuario.provedor_auth == ProvedorAuth.GOOGLE,
            Usuario.provedor_id == google_id,
        )
    )
    usuario = result.scalar_one_or_none()

    if not usuario and email:
        result = await db.execute(select(Usuario).where(Usuario.email == email))
        usuario = result.scalar_one_or_none()
        if usuario:
            usuario.provedor_auth = ProvedorAuth.GOOGLE
            usuario.provedor_id = google_id
            if not usuario.nome and nome:
                usuario.nome = nome

    if not usuario:
        usuario = Usuario(
            email=email,
            nome=nome,
            anonimo=False,
            provedor_auth=ProvedorAuth.GOOGLE,
            provedor_id=google_id,
        )
        db.add(usuario)

    await db.commit()
    await db.refresh(usuario)

    jwt_token = criar_token(str(usuario.id))
    response = RedirectResponse(f"{settings.frontend_url}/auth/callback", status_code=302)
    _set_auth_cookie(response, jwt_token)
    return response


# --- Session ---


@router.get("/me")
async def me(usuario: Usuario = Depends(get_current_user)):
    return {
        "id": str(usuario.id),
        "email": usuario.email,
        "nome": usuario.nome,
        "uf": usuario.uf,
        "provedor_auth": usuario.provedor_auth.value,
    }


class AtualizarPerfilRequest(BaseModel):
    uf: str | None = None
    nome: str | None = None


@router.patch("/me")
async def atualizar_perfil(
    body: AtualizarPerfilRequest,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.uf is not None:
        usuario.uf = body.uf.upper() if body.uf else None
    if body.nome is not None:
        usuario.nome = body.nome or None
    await db.commit()
    await db.refresh(usuario)
    return {
        "id": str(usuario.id),
        "email": usuario.email,
        "nome": usuario.nome,
        "uf": usuario.uf,
        "provedor_auth": usuario.provedor_auth.value,
    }


@router.post("/logout")
async def logout():
    response = RedirectResponse(settings.frontend_url, status_code=302)
    response.delete_cookie("auth_token", path="/")
    return response
