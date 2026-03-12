from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_optional_user
from app.database import get_db
from app.models.base import VotoUsuario
from app.models.usuario import RespostaUsuario, Usuario
from app.services.matching import ranking_parlamentares

router = APIRouter()


class RespostaItem(BaseModel):
    proposicao_id: int
    voto: VotoUsuario
    peso: float = 1.0


class CalcularRequest(BaseModel):
    respostas: list[RespostaItem] = []
    casa: str | None = None
    uf: str | None = None


@router.post("/calcular")
async def calcular(
    request: CalcularRequest,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario | None = Depends(get_optional_user),
):
    respostas = request.respostas

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

    resultados = await ranking_parlamentares(
        db,
        respostas=respostas,
        casa=request.casa,
        uf=request.uf,
    )
    return resultados
