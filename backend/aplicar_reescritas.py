"""Apply rewritten proposição content to the database.

Reads from /tmp/proposicoes_reescritas.json and updates resumo_cidadao + descricao_detalhada
in the database.

Usage:
    python aplicar_reescritas.py [--dry-run] [--limit N]

    Run from backend/ directory with DB access.
"""

import argparse
import asyncio
import json

from sqlalchemy import update

from app.database import async_session
from app.models.proposicao import Proposicao

INPUT_FILE = "/tmp/proposicoes_reescritas.json"


async def apply_rewrites(dry_run: bool = False, limit: int = 0):
    with open(INPUT_FILE) as f:
        items = json.load(f)

    if limit:
        items = items[:limit]

    print(f"Loaded {len(items)} rewritten proposições")

    if dry_run:
        for item in items[:10]:
            old = item.get("resumo_cidadao", "")[:60]
            new = item.get("novo_titulo", "")[:60]
            print(f"  [{item['id']}] {item['tipo']} {item['numero']}/{item['ano']}")
            print(f"    OLD: {old}")
            print(f"    NEW: {new}")
            print()
        if len(items) > 10:
            print(f"  ... e mais {len(items) - 10}")
        return

    async with async_session() as db:
        updated = 0
        for item in items:
            titulo = item.get("novo_titulo")
            descricao = item.get("nova_descricao")

            if not titulo:
                continue

            await db.execute(
                update(Proposicao)
                .where(Proposicao.id == item["id"])
                .values(
                    resumo_cidadao=titulo,
                    descricao_detalhada=descricao,
                )
            )
            updated += 1

            if updated % 50 == 0:
                await db.commit()
                print(f"  {updated} atualizadas...")

        await db.commit()
        print(f"\nCompleto! {updated} proposições atualizadas no banco.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    asyncio.run(apply_rewrites(dry_run=args.dry_run, limit=args.limit))


if __name__ == "__main__":
    main()
