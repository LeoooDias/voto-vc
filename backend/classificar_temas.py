"""Classify proposições by topic using Claude API."""
import asyncio
import json
import os
import sys

import anthropic

from app.database import async_session
from sqlalchemy import text

TEMAS_VALIDOS = [
    "economia", "tributacao", "saude", "educacao", "meio-ambiente",
    "seguranca", "direitos-humanos", "trabalho", "agricultura",
    "defesa", "tecnologia", "corrupcao", "previdencia", "habitacao",
    "transporte", "cultura", "geral",
]

BATCH_SIZE = 25


def build_prompt(items: list[dict]) -> str:
    lines = []
    for item in items:
        resumo = item.get("resumo") or ""
        descricao = item.get("descricao") or ""
        lines.append(
            f"ID:{item['id']} | {item['tipo']} {item['numero']}/{item['ano']}\n"
            f"  Resumo: {resumo}\n"
            f"  Descrição: {descricao}\n"
            f"  Ementa: {item['ementa'][:200]}"
        )
    block = "\n\n".join(lines)

    temas_list = "\n".join(f"- {t}" for t in TEMAS_VALIDOS)

    return f"""Classifique cada proposição legislativa brasileira em exatamente UM tema.

Temas disponíveis:
{temas_list}

Use "geral" apenas quando nenhum outro tema se aplica claramente.

Analise o CONTEÚDO REAL da proposição (resumo e descrição), não apenas palavras soltas na ementa.
Por exemplo, uma proposição sobre o Ministério Público é "seguranca" ou "corrupcao", não "meio-ambiente".

Responda APENAS em JSON válido: array de objetos com "id" e "tema". Nada mais.

Proposições:

{block}"""


def classify_batch(client: anthropic.Anthropic, items: list[dict]) -> list[dict]:
    prompt = build_prompt(items)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    results = json.loads(text)
    # Validate
    for r in results:
        r["id"] = int(r["id"])
        if r["tema"] not in TEMAS_VALIDOS:
            r["tema"] = "geral"
    return results


async def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    async with async_session() as db:
        r = await db.execute(text("""
            SELECT id, tipo, numero, ano, ementa, resumo_cidadao, descricao_detalhada
            FROM proposicoes
            WHERE resumo_cidadao IS NOT NULL
            ORDER BY id
        """))
        rows = r.all()

    items = [
        {"id": row[0], "tipo": row[1], "numero": row[2], "ano": row[3],
         "ementa": row[4], "resumo": row[5], "descricao": row[6]}
        for row in rows
    ]

    print(f"Classifying {len(items)} proposições...")

    client = anthropic.Anthropic(api_key=api_key)
    all_results = []

    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        print(f"Batch {i // BATCH_SIZE + 1} ({len(batch)} items)...", end=" ", flush=True)
        try:
            results = classify_batch(client, batch)
            all_results.extend(results)
            print("OK")
        except Exception as e:
            print(f"Error: {e}")

    # Save to DB
    async with async_session() as db:
        updated = 0
        for r in all_results:
            await db.execute(
                text("UPDATE proposicoes SET tema = :tema WHERE id = :id"),
                {"tema": r["tema"], "id": r["id"]},
            )
            updated += 1
        await db.commit()

    print(f"\nDone: {updated} proposições classified")

    # Show distribution
    from collections import Counter
    dist = Counter(r["tema"] for r in all_results)
    for tema, n in dist.most_common():
        print(f"  {tema:25s} {n:>3d}")


asyncio.run(main())
