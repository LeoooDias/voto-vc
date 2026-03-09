from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.parlamentar import Parlamentar

router = APIRouter()


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
    return result.scalar_one_or_none()
