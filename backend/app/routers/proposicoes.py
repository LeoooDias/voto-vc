from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.proposicao import Proposicao

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

    return {
        "total": total,
        "paginas": (total + itens - 1) // itens,
        "items": [
            {
                "id": p.id,
                "id_externo": p.id_externo,
                "tipo": p.tipo,
                "numero": p.numero,
                "ano": p.ano,
                "ementa": (
                    (p.ementa[:150] + "...") if p.ementa and len(p.ementa) > 150 else p.ementa
                ),
                "resumo_cidadao": p.resumo_cidadao,
                "descricao_detalhada": p.descricao_detalhada,
                "tema": p.tema,
                "substantiva": p.tipo in SUBSTANTIVE_TYPES,
            }
            for p in props
        ],
    }


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
