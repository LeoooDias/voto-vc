from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.base import VotoUsuario
from app.services.matching import ranking_parlamentares

router = APIRouter()


class RespostaItem(BaseModel):
    proposicao_id: int
    voto: VotoUsuario
    peso: float = 1.0


class CalcularRequest(BaseModel):
    respostas: list[RespostaItem]
    casa: str | None = None
    uf: str | None = None


@router.post("/calcular")
async def calcular(request: CalcularRequest, db: AsyncSession = Depends(get_db)):
    resultados = await ranking_parlamentares(
        db,
        respostas=request.respostas,
        casa=request.casa,
        uf=request.uf,
    )
    return resultados
