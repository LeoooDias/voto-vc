from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.base import VotoUsuario
from app.models.usuario import RespostaUsuario, Usuario
from app.services.questionario import montar_questionario

router = APIRouter()


@router.get("/items")
async def obter_questionario(
    n_items: int = 25,
    db: AsyncSession = Depends(get_db),
):
    items = await montar_questionario(db, n_items=n_items)
    return items


class ResponderRequest(BaseModel):
    proposicao_id: int
    voto: VotoUsuario
    peso: float = 1.0


@router.post("/responder")
async def responder(
    request: ResponderRequest,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        insert(RespostaUsuario)
        .values(
            usuario_id=usuario.id,
            proposicao_id=request.proposicao_id,
            voto=request.voto,
            peso=request.peso,
        )
        .on_conflict_do_update(
            constraint="uq_resposta_usuario",
            set_={"voto": request.voto, "peso": request.peso},
        )
    )
    await db.execute(stmt)
    await db.commit()
    return {"ok": True}


@router.get("/respostas")
async def obter_respostas(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RespostaUsuario).where(RespostaUsuario.usuario_id == usuario.id)
    )
    return [
        {
            "proposicao_id": r.proposicao_id,
            "voto": r.voto.value,
            "peso": r.peso,
        }
        for r in result.scalars().all()
    ]


@router.delete("/respostas")
async def limpar_respostas(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(RespostaUsuario).where(RespostaUsuario.usuario_id == usuario.id))
    await db.commit()
    return {"ok": True}
