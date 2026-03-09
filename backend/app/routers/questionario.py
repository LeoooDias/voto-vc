from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.questionario import montar_questionario

router = APIRouter()


@router.get("/items")
async def obter_questionario(
    n_items: int = 25,
    db: AsyncSession = Depends(get_db),
):
    items = await montar_questionario(db, n_items=n_items)
    return items
