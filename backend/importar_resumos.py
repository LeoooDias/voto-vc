"""Import AI-generated summaries and descriptions into the DB."""
import asyncio
import json
import sys

from sqlalchemy import update

from app.database import async_session
from app.models.proposicao import Proposicao


async def importar(input_file: str, field: str):
    with open(input_file) as f:
        items = json.load(f)

    updated = 0
    skipped = 0

    async with async_session() as db:
        for item in items:
            value = item.get(field, "").strip()
            if not value:
                skipped += 1
                continue

            result = await db.execute(
                update(Proposicao)
                .where(Proposicao.id == item["id"])
                .values(**{field: value})
            )
            if result.rowcount:
                updated += 1
            else:
                skipped += 1

        await db.commit()

    print(f"Done: {updated} updated, {skipped} skipped (field: {field})")


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        input_file = sys.argv[1]
        field = sys.argv[2]
    else:
        # Default: import resumo_cidadao
        input_file = "/tmp/proposicoes_resumidas.json"
        field = "resumo_cidadao"

    asyncio.run(importar(input_file, field))
