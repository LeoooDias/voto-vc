"""Chat endpoint for proposição Q&A with streaming."""

import json
import logging
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.posicao import Posicao, PosicaoProposicao
from app.models.proposicao import Proposicao
from app.models.usuario import Usuario
from app.services.chat import stream_chat, stream_posicao_chat

logger = logging.getLogger(__name__)

router = APIRouter()

# Simple in-memory rate limiter per user
_user_timestamps: dict[int, list[float]] = defaultdict(list)


def _parse_rate_limit(limit_str: str) -> tuple[int, int]:
    """Parse 'N/period' into (count, seconds)."""
    count_str, period = limit_str.split("/")
    count = int(count_str)
    periods = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
    seconds = periods.get(period, 3600)
    return count, seconds


def _check_rate_limit(user_id: int) -> None:
    max_count, window = _parse_rate_limit(settings.chat_rate_limit)
    now = time.time()
    cutoff = now - window
    timestamps = _user_timestamps[user_id]
    _user_timestamps[user_id] = [t for t in timestamps if t > cutoff]
    if len(_user_timestamps[user_id]) >= max_count:
        raise HTTPException(
            status_code=429,
            detail=f"Limite de {max_count} mensagens/hora atingido.",
        )
    _user_timestamps[user_id].append(now)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


@router.post("/proposicao/{proposicao_id}")
async def chat_proposicao(
    proposicao_id: int,
    body: ChatRequest,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Chat não configurado.")

    _check_rate_limit(usuario.id)

    prop = await db.get(Proposicao, proposicao_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Proposição não encontrada.")

    history = [{"role": m.role, "content": m.content} for m in body.history]

    async def generate():
        try:
            async for chunk in stream_chat(prop, body.message, history):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error(f"Chat error for proposicao {proposicao_id}: {e}")
            yield f"data: {json.dumps({'error': 'Erro ao gerar resposta. Tente novamente.'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/posicao/{posicao_id}")
async def chat_posicao(
    posicao_id: int,
    body: ChatRequest,
    request: Request,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.anthropic_api_key:
        raise HTTPException(status_code=503, detail="Chat não configurado.")

    _check_rate_limit(usuario.id)

    posicao = await db.get(Posicao, posicao_id)
    if not posicao:
        raise HTTPException(status_code=404, detail="Posição não encontrada.")

    # Load proposições linked to this position
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    stmt = (
        select(PosicaoProposicao)
        .where(PosicaoProposicao.posicao_id == posicao_id)
        .options(selectinload(PosicaoProposicao.proposicao))
    )
    result = await db.execute(stmt)
    pos_props = result.scalars().all()

    proposicoes = []
    for pp in pos_props:
        prop = pp.proposicao
        if prop:
            proposicoes.append(
                {
                    "tipo": prop.tipo,
                    "numero": prop.numero,
                    "ano": prop.ano,
                    "ementa": prop.ementa,
                    "resumo_cidadao": prop.resumo_cidadao,
                    "direcao": pp.direcao.value,
                }
            )

    history = [{"role": m.role, "content": m.content} for m in body.history]

    async def generate():
        try:
            async for chunk in stream_posicao_chat(posicao, proposicoes, body.message, history):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error(f"Chat error for posicao {posicao_id}: {e}")
            yield (f"data: {json.dumps({'error': 'Erro ao gerar resposta. Tente novamente.'})}\n\n")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
