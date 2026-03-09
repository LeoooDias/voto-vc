from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.proposicao import Proposicao

router = APIRouter()


@router.get("/")
async def listar_proposicoes(
    topico: str | None = None,
    ano: int | None = None,
    pagina: int = 1,
    itens: int = 50,
    db: AsyncSession = Depends(get_db),
):
    query = select(Proposicao)
    if ano:
        query = query.where(Proposicao.ano == ano)
    query = query.order_by(Proposicao.ano.desc()).offset((pagina - 1) * itens).limit(itens)
    result = await db.execute(query)
    return result.scalars().all()
