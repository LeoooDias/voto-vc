"""Link existing votações to proposições by parsing descriptions and fetching from API."""

import asyncio
import logging
import re

import httpx
from sqlalchemy import select, text

from app.classification.classifier import classify_proposicao
from app.database import async_session
from app.models.proposicao import Proposicao
from app.models.topico import ProposicaoTopico, Topico
from app.models.votacao import Votacao

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2"

# Map description patterns to API siglaTipo
TIPO_MAP = {
    "Projeto de Lei Complementar": "PLP",
    "Projeto de Decreto Legislativo": "PDL",
    "Projeto de Lei": "PL",
    "Proposta de Emenda à Constituição": "PEC",
    "Medida Provisória": "MPV",
}

PROP_PATTERN = re.compile(
    r"(Projeto de Lei Complementar|Projeto de Decreto Legislativo|Projeto de Lei|"
    r"Proposta de Emenda à Constituição|Medida Provisória)"
    r"[^0-9]*n[ºo°.\s]*([0-9][0-9.]*)[^0-9]*de\s*(\d{4})",
    re.IGNORECASE,
)


def parse_prop_from_description(desc: str) -> tuple[str, str, int] | None:
    """Extract (siglaTipo, numero, ano) from votação description."""
    m = PROP_PATTERN.search(desc or "")
    if not m:
        return None
    tipo_full = m.group(1)
    numero = m.group(2).replace(".", "")
    ano = int(m.group(3))
    sigla = TIPO_MAP.get(tipo_full, "PL")
    return sigla, numero, ano


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


async def fetch_proposicao_from_api(tipo: str, numero: str, ano: int) -> dict | None:
    """Search for a proposição in the API by type, number and year."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(
                f"{CAMARA_API}/proposicoes",
                params={"siglaTipo": tipo, "numero": numero, "ano": ano, "itens": 1},
            )
            dados = r.json().get("dados", [])
            if not dados:
                return None

            # Get full details
            prop_id = dados[0]["id"]
            r2 = await client.get(f"{CAMARA_API}/proposicoes/{prop_id}")
            return r2.json().get("dados", {})
        except Exception as e:
            logger.warning(f"Failed to fetch {tipo} {numero}/{ano}: {e}")
            return None


async def link_votacoes():
    """Find unlinked votações with individual votes, parse descriptions, and link to proposições."""
    async with async_session() as db:
        # Load topic mapping
        topico_mapping = {}
        result = await db.execute(select(Topico))
        for t in result.scalars().all():
            topico_mapping[t.slug] = t.id

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
        for row in rows:
            vot_id, vot_ext, desc, n_votos, sim_count, nao_count = row

            # Parse proposition from description
            parsed = parse_prop_from_description(desc)
            if not parsed:
                logger.info(f"  Could not parse: {desc[:80]}")
                continue

            tipo, numero, ano = parsed
            logger.info(f"  Parsed: {tipo} {numero}/{ano} from votação {vot_ext}")

            # Check if proposição already exists
            prop_id_externo = f"camara_prop_{tipo}_{numero}_{ano}"
            result = await db.execute(
                select(Proposicao).where(Proposicao.id_externo == prop_id_externo)
            )
            proposicao = result.scalar_one_or_none()

            if not proposicao:
                # Fetch from API
                await asyncio.sleep(1)
                prop_raw = await fetch_proposicao_from_api(tipo, numero, ano)

                if prop_raw and prop_raw.get("ementa"):
                    ementa = prop_raw["ementa"]
                    topics = classify_proposicao(ementa, tipo)

                    # Calculate divisiveness
                    total = sim_count + nao_count
                    relevancia = round(min(sim_count, nao_count) / total * 2, 3) if total > 0 else 0

                    proposicao = Proposicao(
                        id_externo=prop_id_externo,
                        casa_origem="camara",
                        tipo=tipo,
                        numero=int(numero),
                        ano=ano,
                        ementa=ementa,
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
                        f"    Created: {tipo} {numero}/{ano} "
                        f"(rel={relevancia}, topics={[t.slug for t in topics[:3]]})"
                    )
                else:
                    logger.info(f"    Not found in API: {tipo} {numero}/{ano}")
                    continue

            # Link votação to proposição
            votacao = await db.get(Votacao, vot_id)
            if votacao:
                votacao.proposicao_id = proposicao.id
                # Update totals from individual votes
                sim_desc, nao_desc, abst_desc = parse_totals_from_description(desc)
                votacao.total_sim = sim_desc or sim_count
                votacao.total_nao = nao_desc or nao_count
                votacao.total_abstencao = abst_desc

                # Update proposição relevância if needed
                total = votacao.total_sim + votacao.total_nao
                if total > 0:
                    rel = round(min(votacao.total_sim, votacao.total_nao) / total * 2, 3)
                    if proposicao.relevancia_score is None or rel > proposicao.relevancia_score:
                        proposicao.relevancia_score = rel

                linked += 1
                logger.info(
                    f"    Linked votação {vot_ext} → {tipo} {numero}/{ano} "
                    f"({votacao.total_sim}×{votacao.total_nao})"
                )

            await db.commit()

        # Also update totals for already-linked votações
        query2 = text("""
            SELECT v.id,
                   SUM(CASE WHEN vp.voto = 'SIM' THEN 1 ELSE 0 END) as sim,
                   SUM(CASE WHEN vp.voto = 'NAO' THEN 1 ELSE 0 END) as nao,
                   SUM(CASE WHEN vp.voto = 'ABSTENCAO' THEN 1 ELSE 0 END) as abst
            FROM votacoes v
            JOIN votos_parlamentares vp ON vp.votacao_id = v.id
            WHERE v.proposicao_id IS NOT NULL AND v.total_sim = 0
            GROUP BY v.id
        """)
        result = await db.execute(query2)
        for row in result.all():
            votacao = await db.get(Votacao, row[0])
            if votacao:
                votacao.total_sim = row[1]
                votacao.total_nao = row[2]
                votacao.total_abstencao = row[3]
        await db.commit()

        logger.info(f"Done! Linked {linked} votações to proposições")


if __name__ == "__main__":
    asyncio.set_event_loop_policy(None)
    asyncio.run(link_votacoes())
