from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.base import VotoUsuario
from app.models.parlamentar import Parlamentar
from app.models.proposicao import Proposicao
from app.models.votacao import Votacao, VotoParlamentar
from app.services.matching import comparar_parlamentar
from app.utils import urls_por_casa

router = APIRouter()


class RespostaItem(BaseModel):
    proposicao_id: int
    voto: VotoUsuario
    peso: float = 1.0


class CompararRequest(BaseModel):
    respostas: list[RespostaItem]


@router.get("/")
async def listar_parlamentares(
    casa: str | None = None,
    uf: str | None = None,
    partido: str | None = None,
    legislatura_atual: bool = True,
    pagina: int = 1,
    itens: int = 50,
    db: AsyncSession = Depends(get_db),
):
    query = select(Parlamentar).options(joinedload(Parlamentar.partido))
    if casa:
        query = query.where(Parlamentar.casa == casa)
    if uf:
        query = query.where(Parlamentar.uf == uf.upper())
    if legislatura_atual:
        query = query.where(Parlamentar.legislatura_atual.is_(True))
    query = query.offset((pagina - 1) * itens).limit(itens)
    result = await db.execute(query)
    return result.scalars().unique().all()


@router.get("/{parlamentar_id}")
async def obter_parlamentar(parlamentar_id: int, db: AsyncSession = Depends(get_db)):
    query = (
        select(Parlamentar)
        .options(joinedload(Parlamentar.partido))
        .where(Parlamentar.id == parlamentar_id)
    )
    result = await db.execute(query)
    parlamentar = result.scalar_one_or_none()
    if not parlamentar:
        raise HTTPException(status_code=404, detail="Parlamentar não encontrado")

    # Get voting history with proposição details
    votos_query = (
        select(
            VotoParlamentar.voto,
            VotoParlamentar.partido_na_epoca,
            Votacao.data,
            Votacao.descricao,
            Proposicao.id,
            Proposicao.tipo,
            Proposicao.numero,
            Proposicao.ano,
            Proposicao.ementa,
            Proposicao.resumo_cidadao,
            Proposicao.descricao_detalhada,
            Proposicao.tema,
            Proposicao.id_externo,
        )
        .join(Votacao, VotoParlamentar.votacao_id == Votacao.id)
        .outerjoin(Proposicao, Votacao.proposicao_id == Proposicao.id)
        .where(VotoParlamentar.parlamentar_id == parlamentar_id)
        .order_by(Votacao.data.desc())
    )
    votos_result = await db.execute(votos_query)

    substantive_types = {"PL", "PEC", "MPV", "PLP", "PDL", "MIP"}
    votos_history = []
    for row in votos_result.all():
        ementa = row[8]
        if ementa and len(ementa) > 150:
            ementa = ementa[:150] + "..."
        votos_history.append(
            {
                "voto": row[0].value,
                "partido_na_epoca": row[1],
                "data": row[2].isoformat() if row[2] else None,
                "descricao_votacao": row[3],
                "proposicao_id": row[4],
                "proposicao_tipo": row[5],
                "proposicao_numero": row[6],
                "proposicao_ano": row[7],
                "proposicao_ementa": ementa,
                "resumo_cidadao": row[9],
                "descricao_detalhada": row[10],
                "tema": row[11],
                "casas": [
                    {"casa": casa, "url": u}
                    for casa, u in urls_por_casa(row[12], row[5], row[6], row[7]).items()
                    if u
                ],
                "substantiva": row[5] in substantive_types if row[5] else False,
            }
        )

    # Vote stats
    stats_query = (
        select(
            VotoParlamentar.voto,
            func.count(VotoParlamentar.id),
        )
        .where(VotoParlamentar.parlamentar_id == parlamentar_id)
        .group_by(VotoParlamentar.voto)
    )
    stats_result = await db.execute(stats_query)
    stats = {row[0].value: row[1] for row in stats_result.all()}

    partido = parlamentar.partido
    return {
        "id": parlamentar.id,
        "nome_parlamentar": parlamentar.nome_parlamentar,
        "nome_civil": parlamentar.nome_civil,
        "casa": parlamentar.casa.value,
        "uf": parlamentar.uf,
        "sexo": parlamentar.sexo,
        "foto_url": parlamentar.foto_url,
        "partido": ({"sigla": partido.sigla, "nome": partido.nome} if partido else None),
        "legislatura_atual": parlamentar.legislatura_atual,
        "stats": stats,
        "votos": votos_history,
    }


@router.post("/{parlamentar_id}/comparacao")
async def comparar(
    parlamentar_id: int,
    body: CompararRequest,
    db: AsyncSession = Depends(get_db),
):
    return await comparar_parlamentar(db, parlamentar_id, body.respostas)
