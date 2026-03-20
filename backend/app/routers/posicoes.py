from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database import get_db
from app.models.base import VotoUsuario
from app.models.posicao import RespostaPosicao
from app.models.usuario import Usuario
from app.services.posicoes import listar_posicoes

router = APIRouter()


@router.get("/items")
async def obter_posicoes(db: AsyncSession = Depends(get_db)):
    return await listar_posicoes(db)


class ResponderPosicaoRequest(BaseModel):
    posicao_id: int
    voto: VotoUsuario
    peso: float = 1.0


class ResponderPosicaoBatchRequest(BaseModel):
    respostas: list[ResponderPosicaoRequest]


@router.post("/responder")
async def responder_posicao(
    request: ResponderPosicaoRequest,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        insert(RespostaPosicao)
        .values(
            usuario_id=usuario.id,
            posicao_id=request.posicao_id,
            voto=request.voto,
            peso=request.peso,
        )
        .on_conflict_do_update(
            constraint="uq_resposta_posicao",
            set_={"voto": request.voto, "peso": request.peso},
        )
    )
    await db.execute(stmt)
    await db.commit()
    return {"ok": True}


@router.post("/responder/batch")
async def responder_posicao_batch(
    request: ResponderPosicaoBatchRequest,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for r in request.respostas:
        stmt = (
            insert(RespostaPosicao)
            .values(
                usuario_id=usuario.id,
                posicao_id=r.posicao_id,
                voto=r.voto,
                peso=r.peso,
            )
            .on_conflict_do_update(
                constraint="uq_resposta_posicao",
                set_={"voto": r.voto, "peso": r.peso},
            )
        )
        await db.execute(stmt)
    await db.commit()
    return {"ok": True, "count": len(request.respostas)}


@router.get("/respostas")
async def obter_respostas_posicoes(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RespostaPosicao).where(RespostaPosicao.usuario_id == usuario.id)
    )
    return [
        {
            "posicao_id": r.posicao_id,
            "voto": r.voto.value,
            "peso": r.peso,
        }
        for r in result.scalars().all()
    ]


@router.delete("/respostas")
async def limpar_respostas_posicoes(
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(delete(RespostaPosicao).where(RespostaPosicao.usuario_id == usuario.id))
    await db.commit()
    return {"ok": True}
