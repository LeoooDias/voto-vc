"""Link unlinked votações to proposições using the Câmara API.

For votações with generic descriptions (e.g. "Rejeitado o Requerimento") that can't be
parsed for proposition info, we fetch the votação details from the API and use the
`proposicoesAfetadas` field to find the parent proposição.
"""

import asyncio
import logging
import re

from sqlalchemy import select, text

from app.classification.classifier import classify_proposicao
from app.database import async_session
from app.ingestion.base import BaseAPIClient
from app.models.proposicao import Proposicao
from app.models.topico import ProposicaoTopico, Topico
from app.models.votacao import Votacao

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2"


def parse_totals_from_description(desc: str) -> tuple[int, int, int]:
    """Extract (sim, nao, abstencao) from description like 'Sim: 286; Não: 111; Abstenção: 1'."""
    sim = nao = abst = 0
    m = re.search(r"Sim:\s*(\d+)", desc or "")
    if m:
        sim = int(m.group(1))
    m = re.search(r"Não:\s*(\d+)", desc or "")
    if m:
        nao = int(m.group(1))
    m = re.search(r"Abstenção:\s*(\d+)", desc or "")
    if m:
        abst = int(m.group(1))
    return sim, nao, abst


async def find_proposicao_by_api_id(db, api_prop_id: int) -> Proposicao | None:
    """Look up an existing proposição by its Câmara API id.

    Checks both id_externo formats used in the codebase:
    - camara_prop_{api_id} (from sync.py and find_divisive.py)
    - camara_prop_{tipo}_{numero}_{ano} (from link_votacoes.py)
    """
    # Primary format
    result = await db.execute(
        select(Proposicao).where(Proposicao.id_externo == f"camara_prop_{api_prop_id}")
    )
    prop = result.scalar_one_or_none()
    if prop:
        return prop

    return None


async def create_proposicao_from_api(
    db, client: BaseAPIClient, api_prop: dict, topico_mapping: dict, sim_count: int, nao_count: int
) -> Proposicao | None:
    """Fetch full proposição details from the API and create a DB record."""
    api_prop_id = api_prop["id"]
    tipo = api_prop.get("siglaTipo", "")
    numero = api_prop.get("numero", 0)
    ano = api_prop.get("ano", 0)
    ementa = api_prop.get("ementa", "")

    # Fetch full details if ementa is missing
    if not ementa:
        try:
            detail = await client.get(f"proposicoes/{api_prop_id}")
            prop_raw = detail.get("dados", {})
            ementa = prop_raw.get("ementa", "")
            tipo = prop_raw.get("siglaTipo", tipo)
            numero = prop_raw.get("numero", numero)
            ano = prop_raw.get("ano", ano)
        except Exception as e:
            logger.warning(f"  Failed to fetch proposição {api_prop_id} details: {e}")
            return None
    else:
        # Still fetch full details for dados_brutos
        try:
            detail = await client.get(f"proposicoes/{api_prop_id}")
            prop_raw = detail.get("dados", {})
        except Exception:
            prop_raw = api_prop

    if not ementa:
        logger.warning(f"  No ementa for proposição {api_prop_id}, skipping")
        return None

    # Classify
    topics = classify_proposicao(ementa, tipo)

    # Calculate relevância
    total = sim_count + nao_count
    relevancia = round(min(sim_count, nao_count) / total * 2, 3) if total > 0 else 0

    prop_id_externo = f"camara_prop_{api_prop_id}"

    proposicao = Proposicao(
        id_externo=prop_id_externo,
        casa_origem="camara",
        tipo=tipo,
        numero=numero,
        ano=ano,
        ementa=ementa,
        ementa_simplificada=ementa[:200] if len(ementa) > 200 else None,
        resumo_cidadao=ementa,  # placeholder
        url_inteiro_teor=prop_raw.get("urlInteiroTeor"),
        situacao=prop_raw.get("statusProposicao", {}).get("descricaoSituacao")
        if isinstance(prop_raw.get("statusProposicao"), dict)
        else None,
        relevancia_score=relevancia,
        dados_brutos=prop_raw,
    )
    db.add(proposicao)
    await db.flush()

    # Save topic classifications
    for tc in topics:
        if tc.slug in topico_mapping:
            db.add(
                ProposicaoTopico(
                    proposicao_id=proposicao.id,
                    topico_id=topico_mapping[tc.slug],
                    confianca=tc.confianca,
                    metodo="heuristic",
                )
            )

    logger.info(
        f"  Created proposição: {tipo} {numero}/{ano} (id_externo={prop_id_externo}, "
        f"rel={relevancia}, topics={[t.slug for t in topics[:3]]})"
    )
    return proposicao


def pick_main_proposition(afetadas: list[dict]) -> dict | None:
    """From proposicoesAfetadas, pick the main proposition (PL, PEC, MPV, PLP, PDL).

    Filters out procedural types (RPD, SBT, PRLE, REQ, etc.) and returns the
    substantive proposition.
    """
    main_types = {"PL", "PEC", "MPV", "PLP", "PDL"}
    candidates = [p for p in afetadas if p.get("siglaTipo") in main_types]
    if candidates:
        return candidates[0]

    # If no main type found, return the first one that has an ementa
    for p in afetadas:
        if p.get("ementa"):
            return p

    return afetadas[0] if afetadas else None


async def link_unlinked_votacoes():
    """Find unlinked votações with 100+ votes, fetch API details, and link to proposições."""
    client = BaseAPIClient(CAMARA_API, delay_between_requests=1.0)

    async with async_session() as db:
        # Load topic mapping
        topico_mapping = {}
        result = await db.execute(select(Topico))
        for t in result.scalars().all():
            topico_mapping[t.slug] = t.id
        logger.info(f"Loaded {len(topico_mapping)} topics")

        # Find votações with 100+ individual votes but no proposicao_id
        query = text("""
            SELECT v.id, v.id_externo, v.descricao,
                   count(vp.id) as n_votos,
                   SUM(CASE WHEN vp.voto = 'SIM' THEN 1 ELSE 0 END) as sim,
                   SUM(CASE WHEN vp.voto = 'NAO' THEN 1 ELSE 0 END) as nao
            FROM votacoes v
            JOIN votos_parlamentares vp ON vp.votacao_id = v.id
            WHERE v.proposicao_id IS NULL
            GROUP BY v.id
            HAVING count(vp.id) > 100
            ORDER BY count(vp.id) DESC
        """)
        result = await db.execute(query)
        rows = result.all()
        logger.info(f"Found {len(rows)} unlinked votações with 100+ votes")

        linked = 0
        skipped = 0

        for row in rows:
            vot_id, vot_ext, desc, n_votos, sim_count, nao_count = row
            logger.info(f"\nProcessing: {vot_ext} ({n_votos} votes)")
            logger.info(f"  Description: {(desc or '')[:100]}")

            # Extract API votação ID from id_externo (strip "camara_" prefix)
            if not vot_ext or not vot_ext.startswith("camara_"):
                logger.warning(f"  Unexpected id_externo format: {vot_ext}, skipping")
                skipped += 1
                continue

            api_vot_id = vot_ext.removeprefix("camara_")
            logger.info(f"  API votação ID: {api_vot_id}")

            # Fetch votação details from API
            try:
                vot_detail = await client.get(f"votacoes/{api_vot_id}")
                vot_data = vot_detail.get("dados", {})
            except Exception as e:
                logger.warning(f"  Failed to fetch votação {api_vot_id}: {e}")
                skipped += 1
                continue

            # Look for proposições in the response
            afetadas = vot_data.get("proposicoesAfetadas", [])
            if not afetadas:
                logger.info("  No proposicoesAfetadas found, skipping")
                skipped += 1
                continue

            logger.info(f"  Found {len(afetadas)} proposicoesAfetadas:")
            for p in afetadas:
                logger.info(f"    - {p.get('siglaTipo')} {p.get('numero')}/{p.get('ano')} (id={p.get('id')})")

            # Pick the main proposition
            main_prop = pick_main_proposition(afetadas)
            if not main_prop:
                logger.info("  Could not identify main proposition, skipping")
                skipped += 1
                continue

            api_prop_id = main_prop["id"]
            logger.info(
                f"  Selected: {main_prop.get('siglaTipo')} {main_prop.get('numero')}/{main_prop.get('ano')} "
                f"(API id={api_prop_id})"
            )

            # Check if proposição already exists in DB
            proposicao = await find_proposicao_by_api_id(db, api_prop_id)

            if proposicao:
                logger.info(f"  Found existing proposição: {proposicao.id_externo} (DB id={proposicao.id})")
            else:
                # Also check by tipo/numero/ano format (used by link_votacoes.py)
                tipo = main_prop.get("siglaTipo", "")
                numero = main_prop.get("numero", 0)
                ano = main_prop.get("ano", 0)
                alt_id = f"camara_prop_{tipo}_{numero}_{ano}"
                result = await db.execute(
                    select(Proposicao).where(Proposicao.id_externo == alt_id)
                )
                proposicao = result.scalar_one_or_none()

                if proposicao:
                    logger.info(f"  Found existing proposição (alt format): {alt_id} (DB id={proposicao.id})")
                else:
                    logger.info("  Proposição not in DB, creating...")
                    proposicao = await create_proposicao_from_api(
                        db, client, main_prop, topico_mapping, sim_count, nao_count
                    )
                    if not proposicao:
                        skipped += 1
                        continue

            # Link votação to proposição
            votacao = await db.get(Votacao, vot_id)
            if votacao:
                votacao.proposicao_id = proposicao.id

                # Update totals from description if available
                sim_desc, nao_desc, abst_desc = parse_totals_from_description(desc)
                votacao.total_sim = sim_desc or sim_count
                votacao.total_nao = nao_desc or nao_count
                votacao.total_abstencao = abst_desc

                # Update proposição relevância if this vote is more divisive
                total = votacao.total_sim + votacao.total_nao
                if total > 0:
                    rel = round(min(votacao.total_sim, votacao.total_nao) / total * 2, 3)
                    if proposicao.relevancia_score is None or rel > proposicao.relevancia_score:
                        proposicao.relevancia_score = rel

                linked += 1
                logger.info(
                    f"  Linked votação {vot_ext} -> proposição {proposicao.id_externo} "
                    f"({votacao.total_sim} sim / {votacao.total_nao} nao)"
                )

            await db.commit()

        logger.info(f"\nDone! Linked {linked} votações, skipped {skipped}")


if __name__ == "__main__":
    asyncio.set_event_loop_policy(None)
    asyncio.run(link_unlinked_votacoes())
