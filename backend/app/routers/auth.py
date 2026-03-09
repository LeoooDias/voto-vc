from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import criar_token, hash_senha, verificar_senha
from app.database import get_db
from app.models.usuario import Usuario

router = APIRouter()


class RegistrarRequest(BaseModel):
    email: EmailStr
    senha: str
    nome: str | None = None
    uf: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


@router.post("/registrar")
async def registrar(request: RegistrarRequest, db: AsyncSession = Depends(get_db)):
    existente = await db.execute(select(Usuario).where(Usuario.email == request.email))
    if existente.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    usuario = Usuario(
        email=request.email,
        senha_hash=hash_senha(request.senha),
        nome=request.nome,
        uf=request.uf,
        anonimo=False,
    )
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    return {"token": criar_token(str(usuario.id)), "usuario_id": str(usuario.id)}


@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Usuario).where(Usuario.email == request.email))
    usuario = result.scalar_one_or_none()
    if not usuario or not verificar_senha(request.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return {"token": criar_token(str(usuario.id)), "usuario_id": str(usuario.id)}
