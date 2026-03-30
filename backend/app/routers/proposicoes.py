from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.proposicao import Proposicao
from app.models.votacao import Votacao
from app.services.orientacao import orientacoes_por_proposicao
from app.utils import urls_por_casa

router = APIRouter()

SUBSTANTIVE_TYPES = {"PL", "PEC", "MPV", "PLP", "PDL", "MIP"}


def _build_filters(
    tema: str | None,
    tipo: str | None,
    ano: int | None,
    substantiva: bool | None,
    busca: str | None,
):
    conditions = []
    if ano:
        conditions.append(Proposicao.ano == ano)
    if tipo:
        conditions.append(Proposicao.tipo == tipo.upper())
    if tema:
        conditions.append(Proposicao.tema == tema)
    if substantiva is True:
        conditions.append(Proposicao.tipo.in_(SUBSTANTIVE_TYPES))
    elif substantiva is False:
        conditions.append(Proposicao.tipo.notin_(SUBSTANTIVE_TYPES))
    if busca:
        conditions.append(
            Proposicao.ementa.ilike(f"%{busca}%") | Proposicao.resumo_cidadao.ilike(f"%{busca}%")
        )
    return conditions


@router.get("/")
async def listar_proposicoes(
    tema: str | None = None,
    tipo: str | None = None,
    ano: int | None = None,
    substantiva: bool | None = None,
    busca: str | None = None,
    lang: str = "pt-BR",
    pagina: int = 1,
    itens: int = 50,
    db: AsyncSession = Depends(get_db),
):
    conditions = _build_filters(tema, tipo, ano, substantiva, busca)

    # Total count
    count_q = select(func.count(Proposicao.id))
    for c in conditions:
        count_q = count_q.where(c)
    total = (await db.execute(count_q)).scalar() or 0

    # Page data
    query = select(Proposicao)
    for c in conditions:
        query = query.where(c)
    query = (
        query.order_by(Proposicao.ano.desc(), Proposicao.id.desc())
        .offset((pagina - 1) * itens)
        .limit(itens)
    )
    result = await db.execute(query)
    props = result.scalars().all()

    # Build casas mapping for these proposições
    prop_ids = [p.id for p in props]
    casas_by_prop: dict[int, list[str]] = {}
    if prop_ids:
        casas_query = (
            select(Votacao.proposicao_id, Votacao.casa)
            .where(Votacao.proposicao_id.in_(prop_ids))
            .distinct()
        )
        casas_result = await db.execute(casas_query)
        for row in casas_result.all():
            casas_by_prop.setdefault(row[0], []).append(
                row[1].lower() if isinstance(row[1], str) else row[1].value.lower()
            )
        for k in casas_by_prop:
            casas_by_prop[k] = sorted(set(casas_by_prop[k]))

    def _tfield(p: Proposicao, field: str) -> str | None:
        if lang == "en":
            val = getattr(p, f"{field}_en", None)
            if val:
                return val
        return getattr(p, field)

    items = []
    for p in props:
        prop_urls = urls_por_casa(p.id_externo, p.tipo, p.numero, p.ano)
        casas = [{"casa": c, "url": prop_urls.get(c)} for c in casas_by_prop.get(p.id, [])]
        items.append(
            {
                "id": p.id,
                "id_externo": p.id_externo,
                "tipo": p.tipo,
                "numero": p.numero,
                "ano": p.ano,
                "ementa": (
                    (p.ementa[:150] + "...") if p.ementa and len(p.ementa) > 150 else p.ementa
                ),
                "resumo_cidadao": _tfield(p, "resumo_cidadao"),
                "descricao_detalhada": _tfield(p, "descricao_detalhada"),
                "tema": p.tema,
                "substantiva": p.tipo in SUBSTANTIVE_TYPES,
                "casas": casas,
            }
        )

    return {
        "total": total,
        "paginas": (total + itens - 1) // itens,
        "items": items,
    }


class BatchRequest(BaseModel):
    ids: list[int]


@router.post("/batch")
async def batch_proposicoes(
    body: BatchRequest,
    lang: str = "pt-BR",
    db: AsyncSession = Depends(get_db),
):
    """Return proposição details for a list of IDs."""
    if not body.ids or len(body.ids) > 500:
        return []

    def _tfield(p: Proposicao, field: str) -> str | None:
        if lang == "en":
            val = getattr(p, f"{field}_en", None)
            if val:
                return val
        return getattr(p, field)

    query = select(Proposicao).where(Proposicao.id.in_(body.ids))
    result = await db.execute(query)
    props = result.scalars().all()

    items = []
    for p in props:
        prop_urls = urls_por_casa(p.id_externo, p.tipo, p.numero, p.ano)
        casas = [{"casa": c, "url": u} for c, u in prop_urls.items() if u]
        items.append(
            {
                "proposicao_id": p.id,
                "tipo": p.tipo,
                "numero": p.numero,
                "ano": p.ano,
                "resumo": _tfield(p, "resumo_cidadao"),
                "descricao_detalhada": _tfield(p, "descricao_detalhada"),
                "tema": p.tema or "geral",
                "casas": casas,
            }
        )
    return items


@router.get("/{proposicao_id}/partidos")
async def partidos_por_proposicao(
    proposicao_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Orientações e distribuição de votos por partido para uma proposição."""
    return await orientacoes_por_proposicao(db, proposicao_id)


@router.get("/filtros")
async def obter_filtros(db: AsyncSession = Depends(get_db)):
    temas_q = (
        select(Proposicao.tema, func.count(Proposicao.id))
        .where(Proposicao.tema.isnot(None))
        .group_by(Proposicao.tema)
        .order_by(func.count(Proposicao.id).desc())
    )
    tipos_q = (
        select(Proposicao.tipo, func.count(Proposicao.id))
        .group_by(Proposicao.tipo)
        .order_by(func.count(Proposicao.id).desc())
    )
    anos_q = select(Proposicao.ano).distinct().order_by(Proposicao.ano.desc())

    temas = await db.execute(temas_q)
    tipos = await db.execute(tipos_q)
    anos = await db.execute(anos_q)

    return {
        "temas": [{"valor": r[0], "count": r[1]} for r in temas.all()],
        "tipos": [{"valor": r[0], "count": r[1]} for r in tipos.all()],
        "anos": [r[0] for r in anos.all()],
    }
