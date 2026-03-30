"""
Batch-translate proposição text fields (resumo_cidadao, descricao_detalhada)
from Portuguese to English using Claude Haiku 4.5.

Idempotent: skips proposições that already have resumo_cidadao_en populated.

Usage:
    cd backend && uv run python scripts/translate_proposicoes.py
    cd backend && uv run python scripts/translate_proposicoes.py --dry-run
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import anthropic
from sqlalchemy import select, update

from app.database import async_session
from app.models.proposicao import Proposicao

MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 10
SLEEP_BETWEEN_BATCHES = 2.0

SYSTEM_PROMPT = (
    "You are a professional translator. Translate the following "
    "Brazilian Portuguese legislative summary to clear, natural "
    "English. Keep it concise and accessible. "
    "Do not add explanations."
)


def build_user_message(
    resumo: str,
    descricao: str | None,
) -> str:
    parts = [f"## Resumo cidadão\n{resumo}"]
    if descricao:
        parts.append(f"\n## Descrição detalhada\n{descricao}")
    parts.append(
        "\n---\n"
        "Return your translation in the exact same format:\n"
        "## Resumo cidadão\n<translated resumo>\n"
    )
    if descricao:
        parts.append("## Descrição detalhada\n<translated descrição>\n")
    return "\n".join(parts)


def parse_translation(text: str, has_descricao: bool) -> tuple[str | None, str | None]:
    """Parse the structured response into resumo_en and descricao_en."""
    resumo_en = None
    descricao_en = None

    sections = text.split("## ")
    for section in sections:
        lower = section.lower()
        if lower.startswith("resumo"):
            # Everything after the header line
            lines = section.split("\n", 1)
            if len(lines) > 1:
                resumo_en = lines[1].strip()
        elif lower.startswith("descri") and has_descricao:
            lines = section.split("\n", 1)
            if len(lines) > 1:
                descricao_en = lines[1].strip()

    return resumo_en, descricao_en


async def translate_proposicao(
    client: anthropic.AsyncAnthropic,
    prop_id: int,
    resumo: str,
    descricao: str | None,
) -> tuple[str | None, str | None]:
    """Call Claude to translate a single proposição."""
    user_msg = build_user_message(resumo, descricao)

    response = await client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    result_text = response.content[0].text
    return parse_translation(result_text, descricao is not None)


async def main():
    parser = argparse.ArgumentParser(description="Translate proposição fields to English")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be translated without making changes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Max proposições to translate (0 = all)",
    )
    args = parser.parse_args()

    # Init Anthropic client (reads ANTHROPIC_API_KEY from env)
    try:
        client = anthropic.AsyncAnthropic()
    except anthropic.AuthenticationError:
        print("ERROR: ANTHROPIC_API_KEY not set or invalid.")
        sys.exit(1)

    async with async_session() as db:
        # Find proposições needing translation
        query = (
            select(Proposicao)
            .where(Proposicao.resumo_cidadao.is_not(None))
            .where(Proposicao.resumo_cidadao_en.is_(None))
            .order_by(Proposicao.id)
        )
        if args.limit > 0:
            query = query.limit(args.limit)

        result = await db.execute(query)
        props = result.scalars().all()

        total = len(props)
        if total == 0:
            print("Nothing to translate — all proposições already done.")
            return

        print(f"Found {total} proposições to translate.")
        if args.dry_run:
            for i, p in enumerate(props, 1):
                has_desc = "+" if p.descricao_detalhada else "-"
                print(f"  {i}/{total}: [{p.tipo} {p.numero}/{p.ano}] (id={p.id}) desc={has_desc}")
            print("\nDry run — no changes made.")
            return

        translated = 0
        errors = 0

        for i, p in enumerate(props, 1):
            label = f"{p.tipo} {p.numero}/{p.ano}"
            print(
                f"Translating {i}/{total}: {label}...",
                end=" ",
                flush=True,
            )

            try:
                resumo_en, descricao_en = await translate_proposicao(
                    client,
                    p.id,
                    p.resumo_cidadao,
                    p.descricao_detalhada,
                )

                if not resumo_en:
                    print("WARN: empty resumo translation, skipping")
                    errors += 1
                    continue

                stmt = (
                    update(Proposicao)
                    .where(Proposicao.id == p.id)
                    .values(
                        resumo_cidadao_en=resumo_en,
                        descricao_detalhada_en=descricao_en,
                    )
                )
                await db.execute(stmt)
                await db.commit()
                translated += 1
                print("OK")

            except Exception as e:
                print(f"ERROR: {e}")
                errors += 1
                await db.rollback()
                continue

            # Sleep between batches
            if i % BATCH_SIZE == 0 and i < total:
                print(f"  -- batch pause ({SLEEP_BETWEEN_BATCHES}s) --")
                await asyncio.sleep(SLEEP_BETWEEN_BATCHES)

        print(f"\nDone! Translated: {translated}, errors: {errors}, total: {total}")


if __name__ == "__main__":
    asyncio.run(main())
