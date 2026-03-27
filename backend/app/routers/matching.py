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
from app.models.posicao import RespostaPosicao
from app.models.usuario import RespostaUsuario, Usuario
from app.services.matching import calcular_matching
from app.services.posicoes import _load_posicoes_map, expandir_posicoes_para_respostas

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class RespostaItem(BaseModel):
    proposicao_id: int
    voto: VotoUsuario
    peso: float = 1.0


class PosicaoRespostaItem(BaseModel):
    posicao_id: int
    voto: VotoUsuario
    peso: float = 1.0


class CalcularRequest(BaseModel):
    respostas: list[RespostaItem] = []
    posicao_respostas: list[PosicaoRespostaItem] = []
    casa: str | None = None
    uf: str | None = None
    limit: int = 50
    apenas_ativos: bool = False
    ultima_decada: bool = False


@router.post("/calcular")
@limiter.limit(settings.rate_limit_matching)
async def calcular(
    request: Request,
    body: CalcularRequest,
    db: AsyncSession = Depends(get_db),
    usuario: Usuario | None = Depends(get_optional_user),
):
    respostas = list(body.respostas)
    posicao_respostas = list(body.posicao_respostas)

    # Se user logado e não mandou respostas, buscar do DB
    if not respostas and not posicao_respostas and usuario:
        result = await db.execute(
            select(RespostaUsuario).where(RespostaUsuario.usuario_id == usuario.id)
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

        # Also load posicao respostas from DB
        pos_result = await db.execute(
            select(RespostaPosicao).where(RespostaPosicao.usuario_id == usuario.id)
        )
        db_pos = pos_result.scalars().all()
        posicao_respostas = [
            PosicaoRespostaItem(
                posicao_id=r.posicao_id,
                voto=r.voto,
                peso=r.peso,
            )
            for r in db_pos
        ]

    # Expand posicao_respostas into per-proposition respostas
    if posicao_respostas:
        posicoes_map = await _load_posicoes_map(db)
        overrides = {
            r.proposicao_id: {
                "proposicao_id": r.proposicao_id,
                "voto": r.voto.value,
                "peso": r.peso,
            }
            for r in respostas
        }
        expanded = expandir_posicoes_para_respostas(
            [
                {"posicao_id": pr.posicao_id, "voto": pr.voto.value, "peso": pr.peso}
                for pr in posicao_respostas
            ],
            posicoes_map,
            overrides,
        )
        # Merge: overrides (direct respostas) take precedence
        seen = {r.proposicao_id for r in respostas}
        for item in expanded:
            if item["proposicao_id"] not in seen:
                respostas.append(RespostaItem(**item))
                seen.add(item["proposicao_id"])

    return await calcular_matching(
        db,
        respostas=respostas,
        casa=body.casa,
        uf=body.uf,
        limit=min(body.limit, 1000),
        apenas_ativos=body.apenas_ativos,
        ultima_decada=body.ultima_decada,
    )
