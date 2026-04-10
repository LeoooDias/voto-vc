from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.questionario import montar_questionario

router = APIRouter()


@router.get("/items")
async def obter_questionario(
    n_items: int = 25,
    exclude: str | None = None,
    lang: str = "pt-BR",
    db: AsyncSession = Depends(get_db),
):
    exclude_ids = set()
    if exclude:
        try:
            exclude_ids = {int(x) for x in exclude.split(",") if x.strip()}
        except ValueError:
            pass
    items = await montar_questionario(db, n_items=n_items, exclude_ids=exclude_ids, lang=lang)
    return items
