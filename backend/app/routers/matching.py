from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_optional_user
from app.database import get_db
from app.models.base import VotoUsuario
from app.models.usuario import RespostaUsuario, Usuario
from app.services.matching import calcular_matching

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class RespostaItem(BaseModel):
    proposicao_id: int
    voto: VotoUsuario
    peso: float = 1.0


class CalcularRequest(BaseModel):
    respostas: list[RespostaItem] = []
    casa: str | None = None
    uf: str | None = None
    limit: int = 50


@router.post("/calcular")
@limiter.limit(settings.rate_limit_matching)
async def calcular(
    request: Request,
    body: CalcularRequest,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario | None = Depends(get_optional_user),
):
    respostas = body.respostas

    # Se user logado e não mandou respostas, usar as do DB
    if not respostas and usuario:
        result = await db.execute(
            select(RespostaUsuario).where(
                RespostaUsuario.usuario_id == usuario.id
            )
        )
        db_respostas = result.scalars().all()
        respostas = [
            RespostaItem(
                proposicao_id=r.proposicao_id,
                voto=r.voto,
                peso=r.peso,
            )
            for r in db_respostas
        ]

    return await calcular_matching(
        db,
        respostas=respostas,
        casa=body.casa,
        uf=body.uf,
        limit=min(body.limit, 1000),
    )
