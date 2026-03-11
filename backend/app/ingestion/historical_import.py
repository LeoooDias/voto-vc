"""Mass historical import of nominal votações from the Câmara API.

Strategy: sweep the /votacoes endpoint in 3-month windows (API max) from 1999 to present.
For each votação with individual votes (nominal), import the proposition, votação, and
individual deputy votes.

Usage:
    python -m app.ingestion.historical_import [--start-year 1999] [--end-year 2026]
"""

import argparse
import asyncio
import logging
import re
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.classification.classifier import classify_proposicao
from app.database import async_session
from app.ingestion.base import BaseAPIClient
from app.models.parlamentar import Parlamentar
from app.models.proposicao import Proposicao
from app.models.topico import ProposicaoTopico, Topico
from app.models.votacao import Votacao, VotoParlamentar

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2"

VOTO_MAP = {
    "Sim": "sim",
    "Não": "nao",
    "Abstenção": "abstencao",
    "Obstrução": "obstrucao",
    "Art. 17": "presente_sem_voto",
}


def generate_quarters(start_year: int, end_year: int) -> list[tuple[str, str]]:
    """Generate (start_date, end_date) pairs for each quarter."""
    quarters = []
    for year in range(start_year, end_year + 1):
        quarters.extend([
            (f"{year}-01-01", f"{year}-03-31"),
            (f"{year}-04-01", f"{year}-06-30"),
            (f"{year}-07-01", f"{year}-09-30"),
            (f"{year}-10-01", f"{year}-12-31"),
        ])
    # Trim future quarters
    today = datetime.now().strftime("%Y-%m-%d")
    return [(s, min(e, today)) for s, e in quarters if s <= today]


async def fetch_all_votacoes_for_quarter(
    client: BaseAPIClient, start_date: str, end_date: str
) -> list[dict]:
    """Fetch all votações in a date range using pagination."""
    all_votacoes = []
    page = 1
    while True:
        try:
            data = await client.get(
                "votacoes",
                params={
                    "dataInicio": start_date,
                    "dataFim": end_date,
                    "ordem": "ASC",
                    "ordenarPor": "dataHoraRegistro",
                    "itens": 100,
                    "pagina": page,
                },
                retries=3,
            )
        except Exception as e:
            logger.warning(f"  Failed to fetch page {page} for {start_date}→{end_date}: {e}")
            break

        items = data.get("dados", [])
        if not items:
            break

        all_votacoes.extend(items)
        if len(items) < 100:
            break
        page += 1

    return all_votacoes


async def historical_import(start_year: int = 1999, end_year: int = 2026):
    """Import all nominal votações from the Câmara API."""
    client = BaseAPIClient(CAMARA_API, delay_between_requests=0.3)
    quarters = generate_quarters(start_year, end_year)
    logger.info(f"Will scan {len(quarters)} quarters from {start_year} to {end_year}")

    async with async_session() as db:
        # Load parlamentar mapping
        result = await db.execute(select(Parlamentar.id_externo, Parlamentar.id))
        parl_mapping = {row[0]: row[1] for row in result.all()}
        logger.info(f"Loaded {len(parl_mapping)} parlamentares")

        # Load topic mapping
        topico_mapping = {}
        result = await db.execute(select(Topico))
        for t in result.scalars().all():
            topico_mapping[t.slug] = t.id
        logger.info(f"Loaded {len(topico_mapping)} topics")

        # Track existing votação IDs to skip quickly
        result = await db.execute(select(Votacao.id_externo))
        existing_vot_ids = {row[0] for row in result.all()}
        logger.info(f"Already have {len(existing_vot_ids)} votações in DB")

        total_imported = 0
        total_skipped = 0
        total_no_votes = 0

        for qi, (start_date, end_date) in enumerate(quarters):
            logger.info(f"\n{'='*60}")
            logger.info(f"Quarter {qi+1}/{len(quarters)}: {start_date} → {end_date}")

            votacoes = await fetch_all_votacoes_for_quarter(client, start_date, end_date)

            # Pre-filter: only votações with dataHoraRegistro (nominal) and vote count hints
            nominal = [
                v for v in votacoes
                if v.get("dataHoraRegistro")
                and f"camara_{v.get('id', '')}" not in existing_vot_ids
            ]
            already = sum(1 for v in votacoes if f"camara_{v.get('id', '')}" in existing_vot_ids)
            total_skipped += already

            logger.info(
                f"  Found {len(votacoes)} votações, {len(nominal)} nominal candidates, "
                f"{already} already in DB"
            )

            quarter_imported = 0
            for vot_raw in nominal:
                api_vot_id = str(vot_raw.get("id", ""))
                id_externo = f"camara_{api_vot_id}"

                # Fetch individual votes
                try:
                    votos_data = await client.get(f"votacoes/{api_vot_id}/votos")
                    votos = votos_data.get("dados", [])
                except Exception as e:
                    logger.warning(f"  Failed to fetch votes for {api_vot_id}: {e}")
                    continue

                # Only import votações with substantial individual votes
                if len(votos) < 50:
                    total_no_votes += 1
                    continue

                # Count votes
                sim = sum(1 for v in votos if v.get("tipoVoto") == "Sim")
                nao = sum(1 for v in votos if v.get("tipoVoto") == "Não")
                abst = sum(1 for v in votos if v.get("tipoVoto") == "Abstenção")
                total_votes = sim + nao
                if total_votes < 30:
                    total_no_votes += 1
                    continue

                # Divisiveness score
                divisiveness = min(sim, nao) / total_votes if total_votes > 0 else 0

                # Try to find/create the proposition
                proposicao_id = None
                proposicao = None

                # Check uriProposicaoPrincipal first
                prop_uri = vot_raw.get("uriProposicaoPrincipal") or vot_raw.get("uriProposicaoObjeto") or ""
                prop_api_id = None
                if "proposicoes" in prop_uri:
                    maybe_id = prop_uri.rstrip("/").split("/")[-1]
                    if maybe_id.isdigit():
                        prop_api_id = maybe_id

                if prop_api_id:
                    # Check existing
                    prop_id_externo = f"camara_prop_{prop_api_id}"
                    result = await db.execute(
                        select(Proposicao).where(Proposicao.id_externo == prop_id_externo)
                    )
                    proposicao = result.scalar_one_or_none()

                    if not proposicao:
                        # Fetch from API
                        try:
                            prop_detail = await client.get(f"proposicoes/{prop_api_id}")
                            prop_raw = prop_detail.get("dados", {})
                            ementa = prop_raw.get("ementa", "")
                            if ementa:
                                tipo = prop_raw.get("siglaTipo", "")
                                numero = prop_raw.get("numero", 0)
                                ano = prop_raw.get("ano", 0)

                                # Also check tipo_numero_ano format
                                alt_id = f"camara_prop_{tipo}_{numero}_{ano}"
                                result = await db.execute(
                                    select(Proposicao).where(Proposicao.id_externo == alt_id)
                                )
                                proposicao = result.scalar_one_or_none()

                                if not proposicao:
                                    topics = classify_proposicao(ementa, tipo)
                                    relevancia = round(min(sim, nao) / total_votes * 2, 3) if total_votes > 0 else 0

                                    proposicao = Proposicao(
                                        id_externo=prop_id_externo,
                                        casa_origem="camara",
                                        tipo=tipo,
                                        numero=numero,
                                        ano=ano,
                                        ementa=ementa,
                                        ementa_simplificada=ementa[:200] if len(ementa) > 200 else None,
                                        resumo_cidadao=ementa,
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
                        except Exception as e:
                            logger.warning(f"  Failed to fetch proposition {prop_api_id}: {e}")

                    if proposicao:
                        proposicao_id = proposicao.id
                        # Update relevância if needed
                        if total_votes > 0:
                            rel = round(min(sim, nao) / total_votes * 2, 3)
                            if proposicao.relevancia_score is None or rel > proposicao.relevancia_score:
                                proposicao.relevancia_score = rel

                # Create votação
                data_str = vot_raw.get("dataHoraRegistro") or vot_raw.get("data", "")
                try:
                    data_dt = datetime.fromisoformat(data_str)
                except (ValueError, TypeError):
                    data_dt = datetime.now()

                votacao = Votacao(
                    id_externo=id_externo,
                    proposicao_id=proposicao_id,
                    casa="camara",
                    data=data_dt,
                    descricao=vot_raw.get("descricao"),
                    resultado=str(vot_raw.get("aprovacao", ""))
                    if vot_raw.get("aprovacao") is not None
                    else None,
                    total_sim=sim,
                    total_nao=nao,
                    total_abstencao=abst,
                    dados_brutos=vot_raw,
                )
                db.add(votacao)
                await db.flush()
                existing_vot_ids.add(id_externo)

                # Save individual votes
                votes_saved = 0
                for vr in votos:
                    dep = vr.get("deputado_", {})
                    dep_id = dep.get("id")
                    if not dep_id:
                        continue

                    parl_ext = f"camara_{dep_id}"
                    parl_db_id = parl_mapping.get(parl_ext)

                    if not parl_db_id:
                        # Create parlamentar on-the-fly for historical deputies
                        parl_db_id = await ensure_parlamentar(
                            db, dep, parl_mapping
                        )
                        if not parl_db_id:
                            continue

                    voto_str = VOTO_MAP.get(vr.get("tipoVoto", ""), "ausente")

                    db.add(
                        VotoParlamentar(
                            votacao_id=votacao.id,
                            parlamentar_id=parl_db_id,
                            voto=voto_str,
                            partido_na_epoca=dep.get("siglaPartido"),
                        )
                    )
                    votes_saved += 1

                quarter_imported += 1
                total_imported += 1

                if total_imported % 10 == 0:
                    await db.commit()
                    logger.info(
                        f"  [{total_imported} imported] {id_externo}: "
                        f"{sim}×{nao} (div={divisiveness:.1%}) "
                        f"prop={'yes' if proposicao_id else 'no'} "
                        f"votes={votes_saved}"
                    )

            await db.commit()
            logger.info(
                f"  Quarter done: {quarter_imported} imported, "
                f"running total: {total_imported} imported, "
                f"{total_skipped} skipped (existing), {total_no_votes} skipped (no nominal votes)"
            )

        logger.info(f"\n{'='*60}")
        logger.info(
            f"DONE! Imported {total_imported} nominal votações, "
            f"skipped {total_skipped} existing, {total_no_votes} non-nominal"
        )


async def ensure_parlamentar(db: AsyncSession, dep_data: dict, parl_mapping: dict) -> int | None:
    """Create a parlamentar record for a historical deputy not yet in the DB."""
    dep_id = dep_data.get("id")
    if not dep_id:
        return None

    parl_ext = f"camara_{dep_id}"

    # Double-check DB
    result = await db.execute(
        select(Parlamentar).where(Parlamentar.id_externo == parl_ext)
    )
    existing = result.scalar_one_or_none()
    if existing:
        parl_mapping[parl_ext] = existing.id
        return existing.id

    nome = dep_data.get("nome", "")
    if not nome:
        return None

    parlamentar = Parlamentar(
        id_externo=parl_ext,
        casa="camara",
        nome_civil=nome,
        nome_parlamentar=nome,
        uf=dep_data.get("siglaUf", ""),
        foto_url=dep_data.get("urlFoto"),
        legislatura_atual=False,
        dados_brutos=dep_data,
    )
    # Need partido
    partido_sigla = dep_data.get("siglaPartido")
    if partido_sigla:
        from app.models.partido import Partido

        result = await db.execute(select(Partido).where(Partido.sigla == partido_sigla))
        partido = result.scalar_one_or_none()
        if not partido:
            partido = Partido(sigla=partido_sigla, nome=partido_sigla)
            db.add(partido)
            await db.flush()
        parlamentar.partido_id = partido.id

    db.add(parlamentar)
    await db.flush()
    parl_mapping[parl_ext] = parlamentar.id
    return parlamentar.id


def main():
    parser = argparse.ArgumentParser(description="Import historical votações from Câmara API")
    parser.add_argument("--start-year", type=int, default=2003, help="Start year (default: 2003)")
    parser.add_argument("--end-year", type=int, default=2026, help="End year (default: 2026)")
    args = parser.parse_args()

    asyncio.set_event_loop_policy(None)
    asyncio.run(historical_import(args.start_year, args.end_year))


if __name__ == "__main__":
    main()
