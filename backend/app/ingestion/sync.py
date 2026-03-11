"""Orchestrates data ingestion from Câmara and Senado APIs."""

import argparse
import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.classification.classifier import classify_proposicao
from app.database import async_session
from app.ingestion.camara import CamaraClient
from app.ingestion.normalize import (
    normalize_deputado,
    normalize_senador,
    normalize_voto_camara,
    normalize_votacao_camara,
)
from app.ingestion.senado import SenadoClient
from app.models.parlamentar import Parlamentar
from app.models.partido import Partido
from app.models.proposicao import Proposicao
from app.models.topico import ProposicaoTopico, Topico
from app.models.votacao import Votacao, VotoParlamentar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def sync_partidos(db: AsyncSession, parlamentares_data: list[dict]) -> dict[str, int]:
    """Ensure all partidos exist and return sigla->id mapping."""
    siglas = {p.get("partido_sigla", "") for p in parlamentares_data if p.get("partido_sigla")}
    mapping = {}

    for sigla in siglas:
        result = await db.execute(select(Partido).where(Partido.sigla == sigla))
        partido = result.scalar_one_or_none()
        if not partido:
            partido = Partido(sigla=sigla, nome=sigla)
            db.add(partido)
            await db.flush()
        mapping[sigla] = partido.id

    return mapping


async def sync_parlamentares(db: AsyncSession, parlamentares_data: list[dict]):
    """Upsert parlamentares."""
    partido_mapping = await sync_partidos(db, parlamentares_data)

    for data in parlamentares_data:
        result = await db.execute(
            select(Parlamentar).where(Parlamentar.id_externo == data["id_externo"])
        )
        parlamentar = result.scalar_one_or_none()

        partido_id = partido_mapping.get(data.get("partido_sigla"))

        if parlamentar:
            parlamentar.nome_parlamentar = data["nome_parlamentar"]
            parlamentar.uf = data["uf"]
            parlamentar.partido_id = partido_id
            parlamentar.foto_url = data.get("foto_url")
            parlamentar.dados_brutos = data.get("dados_brutos")
        else:
            parlamentar = Parlamentar(
                id_externo=data["id_externo"],
                casa=data["casa"],
                nome_civil=data["nome_civil"],
                nome_parlamentar=data["nome_parlamentar"],
                cpf=data.get("cpf"),
                sexo=data.get("sexo"),
                uf=data["uf"],
                foto_url=data.get("foto_url"),
                email=data.get("email"),
                partido_id=partido_id,
                legislatura_atual=data.get("legislatura_atual", False),
                dados_brutos=data.get("dados_brutos"),
            )
            db.add(parlamentar)

    await db.commit()


async def ensure_topicos(db: AsyncSession) -> dict[str, int]:
    """Ensure all canonical topics exist in DB. Return slug->id mapping."""
    from app.classification.topics import TOPICS

    mapping = {}
    for t in TOPICS:
        result = await db.execute(select(Topico).where(Topico.slug == t.slug))
        topico = result.scalar_one_or_none()
        if not topico:
            topico = Topico(
                slug=t.slug, nome=t.nome, descricao=t.descricao, icone=t.icone, cor=t.cor
            )
            db.add(topico)
            await db.flush()
        mapping[t.slug] = topico.id
    await db.commit()
    return mapping


async def sync_votacoes_camara(db: AsyncSession, camara: CamaraClient, max_pages: int = 10):
    """Fetch recent votações from Câmara, with proposições and individual votes."""
    logger.info(f"Fetching votações da Câmara (up to {max_pages} pages)...")

    # Build parlamentar id_externo -> db id mapping
    result = await db.execute(select(Parlamentar.id_externo, Parlamentar.id))
    parl_mapping = {row[0]: row[1] for row in result.all()}

    # Ensure topics exist
    topico_mapping = await ensure_topicos(db)

    votacoes_raw = await camara.fetch_votacoes_recent(max_pages=max_pages)
    logger.info(f"Found {len(votacoes_raw)} votações")

    synced = 0
    for vot_raw in votacoes_raw:
        vot_data = normalize_votacao_camara(vot_raw)

        # Skip if already synced
        existing = await db.execute(
            select(Votacao).where(Votacao.id_externo == vot_data["id_externo"])
        )
        if existing.scalar_one_or_none():
            continue

        # Try to get/create proposição
        proposicao_id = None
        prop_uri = vot_raw.get("uriProposicaoObjeto") or ""
        prop_id_match = prop_uri.rstrip("/").split("/")[-1] if "proposicoes" in prop_uri else None

        if prop_id_match and prop_id_match.isdigit():
            prop_id_externo = f"camara_prop_{prop_id_match}"
            result = await db.execute(
                select(Proposicao).where(Proposicao.id_externo == prop_id_externo)
            )
            proposicao = result.scalar_one_or_none()

            if not proposicao:
                try:
                    prop_raw = await camara.fetch_proposicao(prop_id_match)
                    if prop_raw and prop_raw.get("ementa"):
                        ementa = prop_raw["ementa"]
                        # Classify the proposição
                        topics = classify_proposicao(ementa, prop_raw.get("siglaTipo"))

                        proposicao = Proposicao(
                            id_externo=prop_id_externo,
                            casa_origem="camara",
                            tipo=prop_raw.get("siglaTipo", ""),
                            numero=prop_raw.get("numero", 0),
                            ano=prop_raw.get("ano", 0),
                            ementa=ementa,
                            ementa_simplificada=ementa[:200] if len(ementa) > 200 else None,
                            resumo_cidadao=ementa,  # placeholder — ideally human-written
                            url_inteiro_teor=prop_raw.get("urlInteiroTeor"),
                            situacao=prop_raw.get("statusProposicao", {}).get("descricaoSituacao"),
                            dados_brutos=prop_raw,
                        )
                        db.add(proposicao)
                        await db.flush()

                        # Save topic classifications
                        for tc in topics:
                            if tc.slug in topico_mapping:
                                db.add(ProposicaoTopico(
                                    proposicao_id=proposicao.id,
                                    topico_id=topico_mapping[tc.slug],
                                    confianca=tc.confianca,
                                    metodo="heuristic",
                                ))
                except Exception as e:
                    logger.warning(f"Failed to fetch proposição {prop_id_match}: {e}")

            if proposicao:
                proposicao_id = proposicao.id

        # Parse datetime
        data_str = vot_data.get("data")
        try:
            data_dt = datetime.fromisoformat(data_str) if data_str else datetime.now()
        except (ValueError, TypeError):
            data_dt = datetime.now()

        votacao = Votacao(
            id_externo=vot_data["id_externo"],
            proposicao_id=proposicao_id,
            casa="camara",
            data=data_dt,
            descricao=vot_data.get("descricao"),
            resultado=vot_data.get("resultado"),
            dados_brutos=vot_data.get("dados_brutos"),
        )
        db.add(votacao)
        await db.flush()

        # Fetch individual votes
        try:
            votos_raw = await camara.fetch_votos(str(vot_raw["id"]))
            for vr in votos_raw:
                voto_data = normalize_voto_camara(vr, str(vot_raw["id"]))
                parl_db_id = parl_mapping.get(voto_data["parlamentar_id_externo"])
                if not parl_db_id:
                    continue
                db.add(VotoParlamentar(
                    votacao_id=votacao.id,
                    parlamentar_id=parl_db_id,
                    voto=voto_data["voto"],
                    partido_na_epoca=voto_data.get("partido_na_epoca"),
                    dados_brutos=voto_data.get("dados_brutos"),
                ))
        except Exception as e:
            logger.warning(f"Failed to fetch votos for votação {vot_raw['id']}: {e}")

        synced += 1
        if synced % 10 == 0:
            await db.commit()
            logger.info(f"Synced {synced} votações...")

    await db.commit()
    logger.info(f"Finished syncing {synced} new votações")

    # Compute relevância scores for proposições
    await compute_relevancia(db)


async def compute_relevancia(db: AsyncSession):
    """Set relevancia_score based on how divisive a vote was (close to 50/50 = more relevant)."""
    result = await db.execute(
        select(Votacao).where(Votacao.proposicao_id.is_not(None))
    )
    votacoes = result.scalars().all()

    for v in votacoes:
        total = v.total_sim + v.total_nao
        if total == 0:
            # Count from individual votes
            votos_result = await db.execute(
                select(VotoParlamentar).where(VotoParlamentar.votacao_id == v.id)
            )
            votos = votos_result.scalars().all()
            sim = sum(1 for vp in votos if vp.voto.value == "sim")
            nao = sum(1 for vp in votos if vp.voto.value == "nao")
            total = sim + nao
            v.total_sim = sim
            v.total_nao = nao

        if total > 0 and v.proposicao_id:
            # Score: 1.0 when perfectly split (50/50), 0.0 when unanimous
            ratio = min(v.total_sim, v.total_nao) / total
            relevancia = ratio * 2  # normalize to 0-1

            prop_result = await db.execute(
                select(Proposicao).where(Proposicao.id == v.proposicao_id)
            )
            prop = prop_result.scalar_one_or_none()
            if prop:
                # Keep highest relevância if multiple votações
                if prop.relevancia_score is None or relevancia > prop.relevancia_score:
                    prop.relevancia_score = round(relevancia, 3)

    await db.commit()
    logger.info("Relevância scores computed")


async def run_full_sync():
    """Full sync: parlamentares + votações from recent years."""
    logger.info("Starting full sync...")

    camara = CamaraClient()
    senado = SenadoClient()

    try:
        # Phase 1: Parlamentares
        logger.info("Fetching deputados from Câmara...")
        deputados_raw = await camara.fetch_deputados()
        deputados = [normalize_deputado(d) for d in deputados_raw]
        logger.info(f"Fetched {len(deputados)} deputados")

        logger.info("Fetching senadores from Senado...")
        senadores_raw = await senado.fetch_senadores()
        senadores = [normalize_senador(s) for s in senadores_raw]
        logger.info(f"Fetched {len(senadores)} senadores")

        async with async_session() as db:
            await sync_parlamentares(db, deputados + senadores)
            logger.info("Parlamentares synced successfully")

        # Phase 2: Votações (recent pages)
        async with async_session() as db:
            await sync_votacoes_camara(db, camara, max_pages=5)

    finally:
        await camara.close()
        await senado.close()


async def run_incremental_sync():
    """Incremental sync: recent votações only."""
    logger.info("Incremental sync not yet implemented — running full sync")
    await run_full_sync()


def main():
    parser = argparse.ArgumentParser(description="Sync legislative data")
    parser.add_argument("--full", action="store_true", help="Full sync")
    parser.add_argument("--incremental", action="store_true", help="Incremental sync")
    args = parser.parse_args()

    if args.full:
        asyncio.run(run_full_sync())
    elif args.incremental:
        asyncio.run(run_incremental_sync())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
