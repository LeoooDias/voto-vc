from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.base import VotoUsuario
from app.models.parlamentar import Parlamentar
from app.models.partido import Partido
from app.models.proposicao import Proposicao
from app.models.votacao import Votacao, VotoParlamentar
from app.services.matching import comparar_partido
from app.services.orientacao import (
    _orientacao_efetiva_batch,
    alinhamento_por_orientacao,
    calcular_disciplina,
)
from app.utils import url_camara_from_id_externo

router = APIRouter()


class RespostaItem(BaseModel):
    proposicao_id: int
    voto: VotoUsuario
    peso: float = 1.0


class CompararRequest(BaseModel):
    respostas: list[RespostaItem]
    uf: str | None = None


SUBSTANTIVE_TYPES = {"PL", "PEC", "MPV", "PLP", "PDL", "MIP"}


@router.get("/")
async def listar_partidos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Partido).order_by(Partido.sigla))
    return result.scalars().all()


@router.get("/{partido_id}")
async def obter_partido(
    partido_id: int,
    uf: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Partido).where(Partido.id == partido_id))
    partido = result.scalar_one_or_none()
    if not partido:
        raise HTTPException(status_code=404, detail="Partido não encontrado")

    # Get parlamentar IDs for this party (optionally filtered by UF)
    parl_query = select(Parlamentar.id).where(Parlamentar.partido_id == partido_id)
    if uf:
        parl_query = parl_query.where(Parlamentar.uf == uf.upper())
    parl_result = await db.execute(parl_query)
    parl_ids = [r[0] for r in parl_result.all()]

    if not parl_ids:
        return {
            "id": partido.id,
            "sigla": partido.sigla,
            "nome": partido.nome,
            "total_parlamentares": 0,
            "stats": {},
            "votos": [],
        }

    # Aggregate vote stats
    stats_query = (
        select(VotoParlamentar.voto, func.count(VotoParlamentar.id))
        .where(VotoParlamentar.parlamentar_id.in_(parl_ids))
        .group_by(VotoParlamentar.voto)
    )
    stats_result = await db.execute(stats_query)
    stats = {row[0].value: row[1] for row in stats_result.all()}

    # Voting history: aggregate per proposição
    votos_query = (
        select(
            Proposicao.id,
            Proposicao.tipo,
            Proposicao.numero,
            Proposicao.ano,
            Proposicao.ementa,
            Proposicao.resumo_cidadao,
            Proposicao.descricao_detalhada,
            Proposicao.tema,
            Proposicao.id_externo,
            Votacao.data,
            Votacao.descricao,
            VotoParlamentar.voto,
            func.count(VotoParlamentar.id).label("n"),
            Votacao.id_externo.label("votacao_id_externo"),
        )
        .join(Votacao, VotoParlamentar.votacao_id == Votacao.id)
        .join(Proposicao, Votacao.proposicao_id == Proposicao.id)
        .where(VotoParlamentar.parlamentar_id.in_(parl_ids))
        .group_by(
            Proposicao.id,
            Proposicao.tipo,
            Proposicao.numero,
            Proposicao.ano,
            Proposicao.ementa,
            Proposicao.resumo_cidadao,
            Proposicao.descricao_detalhada,
            Proposicao.tema,
            Proposicao.id_externo,
            Votacao.data,
            Votacao.descricao,
            VotoParlamentar.voto,
            Votacao.id_externo,
        )
        .order_by(Votacao.data.desc())
    )
    votos_result = await db.execute(votos_query)

    # Group by proposição, track votacao id_externo per prop
    prop_map: dict[int, dict] = {}
    prop_votacao_ids: dict[int, set[str]] = {}
    for row in votos_result.all():
        prop_id = row[0]
        votacao_id_ext = row[13]
        if prop_id not in prop_map:
            prop_map[prop_id] = {
                "proposicao_id": prop_id,
                "proposicao_tipo": row[1],
                "proposicao_numero": row[2],
                "proposicao_ano": row[3],
                "proposicao_ementa": (
                    (row[4][:150] + "...") if row[4] and len(row[4]) > 150 else row[4]
                ),
                "resumo_cidadao": row[5],
                "descricao_detalhada": row[6],
                "tema": row[7],
                "url_camara": url_camara_from_id_externo(row[8]),
                "data": row[9].isoformat() if row[9] else None,
                "descricao_votacao": row[10],
                "substantiva": row[1] in SUBSTANTIVE_TYPES if row[1] else False,
                "breakdown": {},
                "orientacao": None,
            }
            prop_votacao_ids[prop_id] = set()
        prop_map[prop_id]["breakdown"][row[11].value] = row[12]
        if votacao_id_ext:
            prop_votacao_ids[prop_id].add(votacao_id_ext)

    # Resolve orientações do partido para todas as votações
    all_votacao_ids = []
    for ids in prop_votacao_ids.values():
        all_votacao_ids.extend(ids)

    if all_votacao_ids:
        try:
            orientacoes = await _orientacao_efetiva_batch(db, partido.sigla, all_votacao_ids)
            for prop_id, vot_ids in prop_votacao_ids.items():
                for vot_id in vot_ids:
                    o = orientacoes.get(vot_id)
                    if o is not None:
                        prop_map[prop_id]["orientacao"] = o.value
                        break
        except Exception:
            # Table may not exist yet (migration pending)
            pass

    return {
        "id": partido.id,
        "sigla": partido.sigla,
        "nome": partido.nome,
        "total_parlamentares": len(parl_ids),
        "stats": stats,
        "votos": list(prop_map.values()),
    }


@router.post("/{partido_id}/comparacao")
async def comparar(
    partido_id: int,
    body: CompararRequest,
    db: AsyncSession = Depends(get_db),
):
    return await comparar_partido(db, partido_id, body.respostas, uf=body.uf)


@router.post("/{sigla}/alinhamento")
async def alinhamento_partido(
    sigla: str,
    body: CompararRequest,
    db: AsyncSession = Depends(get_db),
):
    """Alinhamento usuário–partido via orientações de bancada."""
    # Verificar se o partido existe
    result = await db.execute(select(Partido).where(Partido.sigla == sigla.upper()))
    partido = result.scalar_one_or_none()
    if not partido:
        raise HTTPException(status_code=404, detail="Partido não encontrado")

    return await alinhamento_por_orientacao(db, partido.sigla, body.respostas, uf=body.uf)


@router.get("/{partido_id}/disciplina")
async def disciplina_partido(
    partido_id: int,
    uf: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Disciplina partidária: % de vezes que parlamentares seguiram a orientação."""
    result = await db.execute(select(Partido).where(Partido.id == partido_id))
    partido = result.scalar_one_or_none()
    if not partido:
        raise HTTPException(status_code=404, detail="Partido não encontrado")

    return await calcular_disciplina(db, partido.sigla, uf=uf)
