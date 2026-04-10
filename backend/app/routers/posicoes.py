from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.posicoes import listar_posicoes

router = APIRouter()


@router.get("/items")
async def obter_posicoes(lang: str = "pt-BR", db: AsyncSession = Depends(get_db)):
    return await listar_posicoes(db, lang=lang)
