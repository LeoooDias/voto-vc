from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.partido import Partido

router = APIRouter()


@router.get("/")
async def listar_partidos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Partido).order_by(Partido.sigla))
    return result.scalars().all()


@router.get("/{sigla}")
async def obter_partido(sigla: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Partido).where(Partido.sigla == sigla.upper()))
    return result.scalar_one_or_none()
