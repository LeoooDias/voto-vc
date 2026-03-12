from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.proposicao import Proposicao

router = APIRouter()

SUBSTANTIVE_TYPES = {"PL", "PEC", "MPV", "PLP", "PDL", "MIP"}


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
    query = select(Proposicao)
    if ano:
        query = query.where(Proposicao.ano == ano)
    if tipo:
        query = query.where(Proposicao.tipo == tipo.upper())
    if tema:
        query = query.where(Proposicao.tema == tema)
    if substantiva is True:
        query = query.where(Proposicao.tipo.in_(SUBSTANTIVE_TYPES))
    elif substantiva is False:
        query = query.where(Proposicao.tipo.notin_(SUBSTANTIVE_TYPES))
    if busca:
        query = query.where(
            Proposicao.ementa.ilike(f"%{busca}%")
            | Proposicao.resumo_cidadao.ilike(f"%{busca}%")
        )
    query = (
        query.order_by(Proposicao.ano.desc(), Proposicao.id.desc())
        .offset((pagina - 1) * itens)
        .limit(itens)
    )
    result = await db.execute(query)
    props = result.scalars().all()

    return [
        {
            "id": p.id,
            "tipo": p.tipo,
            "numero": p.numero,
            "ano": p.ano,
            "ementa": (
                (p.ementa[:150] + "...") if p.ementa and len(p.ementa) > 150
                else p.ementa
            ),
            "resumo_cidadao": p.resumo_cidadao,
            "tema": p.tema,
            "substantiva": p.tipo in SUBSTANTIVE_TYPES,
        }
        for p in props
    ]


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
    anos_q = (
        select(Proposicao.ano)
        .distinct()
        .order_by(Proposicao.ano.desc())
    )

    temas = await db.execute(temas_q)
    tipos = await db.execute(tipos_q)
    anos = await db.execute(anos_q)

    return {
        "temas": [{"valor": r[0], "count": r[1]} for r in temas.all()],
        "tipos": [{"valor": r[0], "count": r[1]} for r in tipos.all()],
        "anos": [r[0] for r in anos.all()],
    }
