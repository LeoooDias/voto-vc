import uuid

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verificar_token
from app.database import get_db
from app.models.usuario import Usuario


async def get_current_user(
    auth_token: str = Cookie(), db: AsyncSession = Depends(get_db)
) -> Usuario:
    user_id = verificar_token(auth_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    result = await db.execute(select(Usuario).where(Usuario.id == uuid.UUID(user_id)))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    return usuario


async def get_optional_user(
    auth_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> Usuario | None:
    if not auth_token:
        return None
    user_id = verificar_token(auth_token)
    if not user_id:
        return None
    result = await db.execute(select(Usuario).where(Usuario.id == uuid.UUID(user_id)))
    return result.scalar_one_or_none()
