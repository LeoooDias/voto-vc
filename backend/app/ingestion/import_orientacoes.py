"""Bulk import orientações de bancada from Câmara CSV files.

Downloads and imports party voting orientations from dadosabertos.camara.leg.br.

Usage:
    python -m app.ingestion.import_orientacoes [--start-year 2003] [--end-year 2026] [--data-dir PATH]
"""

import argparse
import asyncio
import csv
import logging
import os
import re

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.base import ORIENTACAO_NORMALIZADA
from app.models.partido import BlocoParlamentar, OrientacaoBancada, Partido, bloco_partido

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = os.path.expanduser("~/Downloads/camara-csv")

CSV_BASE_URL = "https://dadosabertos.camara.leg.br/arquivos/votacoesOrientacoes/csv"

# Siglas that are meta-groups, not real parties/federations
META_GROUPS = {"Governo", "Oposição", "Maioria", "Minoria", "Gov.", "Minoria ", "Maioria "}

# Regex to parse federation siglas like "Fdr PT-PCdoB-PV"
FEDERATION_RE = re.compile(r"^Fdr?\s+(.+)$")


def download_csv(year: int, data_dir: str) -> str:
    """Download CSV for a year if not already present. Returns file path."""
    os.makedirs(data_dir, exist_ok=True)
    filename = f"votacoesOrientacoes-{year}.csv"
    filepath = os.path.join(data_dir, filename)

    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        return filepath

    url = f"{CSV_BASE_URL}/{filename}"
    logger.info(f"Downloading {url}...")
    try:
        with httpx.Client(timeout=120.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
        logger.info(f"  Downloaded {len(response.content)} bytes")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning(f"  CSV not found for {year} (404)")
            return ""
        raise

    return filepath


def parse_federation_parties(sigla: str) -> list[str] | None:
    """Parse 'Fdr PT-PCdoB-PV' → ['PT', 'PCdoB', 'PV']. Returns None if not a federation."""
    match = FEDERATION_RE.match(sigla.strip())
    if not match:
        return None
    parties_str = match.group(1)
    parties = [p.strip() for p in parties_str.split("-") if p.strip()]
    if len(parties) < 2:
        return None
    return parties


async def ensure_blocos(
    db: AsyncSession,
    sigla_csv: str,
    party_siglas: list[str],
    partido_map: dict[str, int],
) -> None:
    """Create BlocoParlamentar + bloco_partido links for a federation if not exists."""
    result = await db.execute(
        select(BlocoParlamentar).where(BlocoParlamentar.sigla_csv == sigla_csv)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return

    bloco = BlocoParlamentar(
        nome=sigla_csv,
        casa="camara",
        legislatura=57,
        federacao=True,
        sigla_csv=sigla_csv,
    )
    db.add(bloco)
    await db.flush()

    for sigla in party_siglas:
        partido_id = partido_map.get(sigla)
        if partido_id:
            await db.execute(
                bloco_partido.insert().values(bloco_id=bloco.id, partido_id=partido_id)
            )

    logger.info(f"  Created bloco '{sigla_csv}' with parties: {party_siglas}")


async def import_orientacoes_year(
    db: AsyncSession,
    year: int,
    data_dir: str,
    existing_votacao_ids: set[str],
    partido_map: dict[str, int],
) -> int:
    """Import orientações for a single year. Returns count of imported rows."""
    filepath = download_csv(year, data_dir)
    if not filepath:
        return 0

    logger.info(f"\nImporting orientações {year}...")

    imported = 0
    skipped_votacao = 0
    skipped_orientacao = 0
    seen_blocos: set[str] = set()

    with open(filepath, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            id_votacao_csv = row.get("idVotacao", "").strip()
            if not id_votacao_csv:
                continue

            id_votacao = f"camara_{id_votacao_csv}"

            if id_votacao not in existing_votacao_ids:
                skipped_votacao += 1
                continue

            sigla_bancada = row.get("siglaBancada", "").strip()
            if not sigla_bancada:
                continue

            orientacao_raw = row.get("orientacao", "").strip()
            orientacao_norm = ORIENTACAO_NORMALIZADA.get(orientacao_raw)

            if not orientacao_norm:
                if orientacao_raw and orientacao_raw != "-":
                    skipped_orientacao += 1
                    if skipped_orientacao <= 10:
                        logger.warning(
                            f"  Unknown orientação: '{orientacao_raw}' (bancada={sigla_bancada})"
                        )
                continue

            # Try to create bloco for federations
            if sigla_bancada not in seen_blocos and sigla_bancada not in META_GROUPS:
                seen_blocos.add(sigla_bancada)
                federation_parties = parse_federation_parties(sigla_bancada)
                if federation_parties and not sigla_bancada.startswith("Bl "):
                    await ensure_blocos(db, sigla_bancada, federation_parties, partido_map)

            orientacao_obj = OrientacaoBancada(
                id_votacao=id_votacao,
                sigla_bancada=sigla_bancada,
                uri_bancada=row.get("uriBancada", "").strip() or None,
                orientacao_raw=orientacao_raw,
                orientacao=orientacao_norm,
                sigla_orgao=row.get("siglaOrgao", "").strip() or None,
            )
            await db.merge(orientacao_obj)
            imported += 1

            if imported % 500 == 0:
                await db.commit()
                logger.info(f"  [{imported} orientações importadas...]")

    await db.commit()
    logger.info(
        f"  Year {year}: {imported} imported, "
        f"{skipped_votacao} skipped (no votação), "
        f"{skipped_orientacao} skipped (unknown orientação)"
    )
    return imported


async def import_orientacoes(
    start_year: int = 2003, end_year: int = 2026, data_dir: str = DEFAULT_DATA_DIR
):
    """Main orchestrator: import orientações for all years."""
    logger.info(f"Importing orientações from {data_dir}, years {start_year}-{end_year}")

    async with async_session() as db:
        # Load existing votação IDs
        from app.models.votacao import Votacao

        result = await db.execute(select(Votacao.id_externo))
        existing_votacao_ids = {row[0] for row in result.all()}
        logger.info(f"Existing votações: {len(existing_votacao_ids)}")

        # Load partido mapping
        result = await db.execute(select(Partido.sigla, Partido.id))
        partido_map = {row[0]: row[1] for row in result.all()}
        logger.info(f"Existing partidos: {len(partido_map)}")

        total = 0
        for ano in range(start_year, end_year + 1):
            count = await import_orientacoes_year(
                db, ano, data_dir, existing_votacao_ids, partido_map
            )
            total += count

        logger.info(f"\n{'=' * 60}")
        logger.info(f"IMPORT COMPLETE: {total} orientações imported")


def main():
    parser = argparse.ArgumentParser(
        description="Import orientações de bancada from Câmara CSV files"
    )
    parser.add_argument("--start-year", type=int, default=2003)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    args = parser.parse_args()

    asyncio.set_event_loop_policy(None)
    asyncio.run(import_orientacoes(args.start_year, args.end_year, args.data_dir))


if __name__ == "__main__":
    main()
