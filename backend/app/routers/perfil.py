import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.base import VotoUsuario
from app.models.perfil import PerfilCompartilhado
from app.models.proposicao import Proposicao
from app.services.matching import calcular_matching
from app.services.og_image import gerar_og_image
from app.services.posicoes import _load_posicoes_map, expandir_posicoes_para_respostas

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class RespostaItem(BaseModel):
    proposicao_id: int
    voto: VotoUsuario
    peso: float = 1.0


class PosicaoRespostaItem(BaseModel):
    posicao_id: int
    voto: VotoUsuario
    peso: float = 1.0


class CompartilharRequest(BaseModel):
    respostas: list[RespostaItem] = []
    posicao_respostas: list[PosicaoRespostaItem] = []


def _gerar_slug() -> str:
    return secrets.token_urlsafe(5)  # 7 chars base64url


def _hash_ip(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()


async def _expandir_respostas(
    db: AsyncSession,
    respostas: list[RespostaItem],
    posicao_respostas: list[PosicaoRespostaItem],
) -> list[RespostaItem]:
    """Merge direct respostas with expanded posicao_respostas."""
    all_respostas = list(respostas)
    if posicao_respostas:
        posicoes_map = await _load_posicoes_map(db)
        overrides = {
            r.proposicao_id: {
                "proposicao_id": r.proposicao_id,
                "voto": r.voto.value,
                "peso": r.peso,
            }
            for r in respostas
        }
        expanded = expandir_posicoes_para_respostas(
            [
                {"posicao_id": pr.posicao_id, "voto": pr.voto.value, "peso": pr.peso}
                for pr in posicao_respostas
            ],
            posicoes_map,
            overrides,
        )
        seen = {r.proposicao_id for r in respostas}
        for item in expanded:
            if item["proposicao_id"] not in seen:
                all_respostas.append(RespostaItem(**item))
                seen.add(item["proposicao_id"])
    return all_respostas


async def _buscar_votos_detalhados(
    db: AsyncSession,
    respostas: list[RespostaItem],
) -> list[dict]:
    """Build votos_detalhados with proposicao metadata."""
    prop_ids = [r.proposicao_id for r in respostas if r.voto.value in ("sim", "nao") and r.peso > 0]
    if not prop_ids:
        return []

    result = await db.execute(
        select(
            Proposicao.id,
            Proposicao.tipo,
            Proposicao.numero,
            Proposicao.ano,
            Proposicao.resumo_cidadao,
        ).where(Proposicao.id.in_(prop_ids))
    )
    props = {row[0]: row for row in result.all()}

    voto_map = {r.proposicao_id: r for r in respostas}
    votos = []
    for pid in prop_ids:
        prop = props.get(pid)
        if not prop:
            continue
        r = voto_map[pid]
        votos.append(
            {
                "proposicao_id": pid,
                "tipo": prop[1],
                "numero": prop[2],
                "ano": prop[3],
                "resumo": prop[4] or "",
                "voto": r.voto.value,
                "peso": r.peso,
            }
        )
    return votos


@router.post("/compartilhar")
@limiter.limit(settings.rate_limit_share)
async def compartilhar(
    request: Request,
    body: CompartilharRequest,
    db: AsyncSession = Depends(get_db),
):
    all_respostas = await _expandir_respostas(db, body.respostas, body.posicao_respostas)

    if not all_respostas:
        raise HTTPException(status_code=422, detail="Nenhuma resposta fornecida.")

    # Calculate matching (no filters — full snapshot)
    resultado = await calcular_matching(db, respostas=all_respostas)

    # Build votos_detalhados
    votos_detalhados = await _buscar_votos_detalhados(db, all_respostas)

    # Build respostas snapshot
    respostas_snapshot = {
        "respostas": [
            {"proposicao_id": r.proposicao_id, "voto": r.voto.value, "peso": r.peso}
            for r in body.respostas
        ],
        "posicao_respostas": [
            {"posicao_id": pr.posicao_id, "voto": pr.voto.value, "peso": pr.peso}
            for pr in body.posicao_respostas
        ],
        "votos_detalhados": votos_detalhados,
    }

    total_respostas = len(
        [r for r in all_respostas if r.voto.value in ("sim", "nao") and r.peso > 0]
    )

    # Generate slug with collision retry
    ip = get_remote_address(request) or "unknown"
    for _ in range(5):
        slug = _gerar_slug()
        existing = await db.execute(
            select(PerfilCompartilhado.id).where(PerfilCompartilhado.slug == slug)
        )
        if existing.scalar_one_or_none() is None:
            break
    else:
        raise HTTPException(status_code=500, detail="Erro ao gerar link. Tente novamente.")

    perfil = PerfilCompartilhado(
        slug=slug,
        respostas=respostas_snapshot,
        resultado_parlamentares=resultado["parlamentares"],
        resultado_partidos=resultado["partidos"],
        total_respostas=total_respostas,
        ip_hash=_hash_ip(ip),
    )
    db.add(perfil)
    await db.commit()

    return {
        "slug": slug,
        "url": f"{settings.frontend_url}/p/{slug}",
    }


@router.get("/{slug}")
async def buscar_perfil(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PerfilCompartilhado).where(PerfilCompartilhado.slug == slug))
    perfil = result.scalar_one_or_none()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado.")

    votos_detalhados = perfil.respostas.get("votos_detalhados", []) if perfil.respostas else []

    return {
        "slug": perfil.slug,
        "created_at": perfil.created_at.isoformat(),
        "total_respostas": perfil.total_respostas,
        "parlamentares": perfil.resultado_parlamentares,
        "partidos": perfil.resultado_partidos,
        "votos_detalhados": votos_detalhados,
    }


@router.get("/{slug}/og.png")
async def og_image(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PerfilCompartilhado).where(PerfilCompartilhado.slug == slug))
    perfil = result.scalar_one_or_none()
    if not perfil:
        raise HTTPException(status_code=404, detail="Perfil não encontrado.")

    img_bytes = gerar_og_image(
        partidos=perfil.resultado_partidos[:3],
        total_respostas=perfil.total_respostas,
        slug=perfil.slug,
    )

    return Response(
        content=img_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=604800, immutable"},
    )
