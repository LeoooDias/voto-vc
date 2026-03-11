"""Process remaining proposições: summarize + enrich + classify + import to DB.

All-in-one pipeline. Reads from /tmp/proposicoes_restantes.json.
Requires ANTHROPIC_API_KEY environment variable.
"""
import asyncio
import json
import os
import sys
import time

import anthropic
import httpx

INPUT_FILE = "/tmp/proposicoes_restantes.json"
BATCH_SIZE = 10

from app.database import async_session
from sqlalchemy import text


# --- Step 1: Summarize ---

def build_summary_prompt(items: list[dict]) -> str:
    lines = []
    for item in items:
        lines.append(
            f"ID:{item['id']} | {item['tipo']} {item['numero']}/{item['ano']} | "
            f"Ementa: {item['ementa'][:300]}"
        )
    block = "\n\n".join(lines)
    return f"""Você é um especialista em traduzir legislação brasileira para linguagem simples e acessível.

Para cada proposição abaixo, gere um resumo curto (1-2 frases, máximo 120 caracteres) que:
- Explique o efeito prático na vida do cidadão
- Use linguagem simples, sem jargão jurídico
- Seja neutro (não tome posição a favor ou contra)
- Comece com um verbo no presente (ex: "Permite...", "Proíbe...", "Muda...")

Responda APENAS em JSON válido, como array de objetos com "id" e "resumo". Nada mais.

Proposições:

{block}"""


# --- Step 2: Enrich ---

def search_web(query: str) -> str:
    try:
        r = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        snippets = []
        for marker in ['class="result__snippet">', 'class="result__title">']:
            parts = r.text.split(marker)
            for part in parts[1:6]:
                end = part.find("</")
                if end > 0:
                    snippet = part[:end].replace("<b>", "").replace("</b>", "").strip()
                    if snippet:
                        snippets.append(snippet)
        return "\n".join(snippets[:8])
    except Exception:
        return ""


def build_enrich_prompt(item: dict, web_context: str) -> str:
    return f"""Você é um especialista em traduzir legislação brasileira para linguagem acessível.

Gere uma descrição detalhada (3-5 frases, máximo 300 caracteres) desta proposição legislativa.

A descrição deve:
- Explicar concretamente O QUE muda na prática (valores, percentuais, prazos quando disponíveis)
- Responder: "quem é afetado?" e "o que muda pra essa pessoa?"
- Usar linguagem simples, sem jargão jurídico
- Ser neutra (não tomar posição)
- NÃO repetir o resumo curto já existente

Proposição: {item['tipo']} {item['numero']}/{item['ano']}
Resumo curto: {item.get('resumo_cidadao', '')}
Ementa oficial: {item['ementa'][:500]}

Contexto da web sobre esta proposição:
{web_context}

Responda APENAS com o texto da descrição, sem aspas nem formatação."""


# --- Step 3: Classify ---

TEMAS_VALIDOS = [
    "economia", "tributacao", "saude", "educacao", "meio-ambiente",
    "seguranca", "direitos-humanos", "trabalho", "agricultura",
    "defesa", "tecnologia", "corrupcao", "previdencia", "habitacao",
    "transporte", "cultura", "geral",
]


def build_classify_prompt(items: list[dict]) -> str:
    lines = []
    for item in items:
        lines.append(
            f"ID:{item['id']} | {item['tipo']} {item['numero']}/{item['ano']}\n"
            f"  Resumo: {item.get('resumo_cidadao', '')}\n"
            f"  Descrição: {item.get('descricao_detalhada', '')}\n"
            f"  Ementa: {item['ementa'][:200]}"
        )
    block = "\n\n".join(lines)
    temas_list = "\n".join(f"- {t}" for t in TEMAS_VALIDOS)
    return f"""Classifique cada proposição legislativa brasileira em exatamente UM tema.

Temas disponíveis:
{temas_list}

Use "geral" apenas quando nenhum outro tema se aplica claramente.
Analise o CONTEÚDO REAL da proposição (resumo e descrição), não apenas palavras soltas na ementa.

Responda APENAS em JSON válido: array de objetos com "id" e "tema". Nada mais.

Proposições:

{block}"""


def parse_json_response(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text)


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    with open(INPUT_FILE) as f:
        items = json.load(f)

    print(f"=== Processing {len(items)} proposições ===\n")

    client = anthropic.Anthropic(api_key=api_key)

    # Step 1: Summarize in batches
    print("--- Step 1: Generating summaries ---")
    summary_map = {}
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]
        print(f"  Batch {i // BATCH_SIZE + 1}/{(len(items) + BATCH_SIZE - 1) // BATCH_SIZE}...", end=" ", flush=True)
        try:
            prompt = build_summary_prompt(batch)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            results = parse_json_response(response.content[0].text)
            for r in results:
                summary_map[int(r["id"])] = r["resumo"]
            print(f"OK ({len(results)} summaries)")
        except Exception as e:
            print(f"Error: {e}")

    for item in items:
        item["resumo_cidadao"] = summary_map.get(item["id"], "")

    print(f"  Total: {len(summary_map)} summaries generated\n")

    # Step 2: Enrich with web search + detailed description
    print("--- Step 2: Enriching with detailed descriptions ---")
    for i, item in enumerate(items):
        if not item.get("resumo_cidadao"):
            continue
        label = f"{item['tipo']} {item['numero']}/{item['ano']}"
        print(f"  [{i+1}/{len(items)}] {label}...", end=" ", flush=True)
        try:
            query = f"{item['tipo']} {item['numero']}/{item['ano']} câmara deputados"
            web_context = search_web(query)
            prompt = build_enrich_prompt(item, web_context)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            item["descricao_detalhada"] = response.content[0].text.strip()
            print(f"OK")
            time.sleep(0.3)
        except Exception as e:
            print(f"Error: {e}")
            item["descricao_detalhada"] = ""

    enriched = sum(1 for item in items if item.get("descricao_detalhada"))
    print(f"  Total: {enriched} descriptions generated\n")

    # Step 3: Classify in batches
    print("--- Step 3: Classifying by topic ---")
    classify_items = [item for item in items if item.get("resumo_cidadao")]
    tema_map = {}
    for i in range(0, len(classify_items), 25):
        batch = classify_items[i:i + 25]
        print(f"  Batch {i // 25 + 1}/{(len(classify_items) + 24) // 25}...", end=" ", flush=True)
        try:
            prompt = build_classify_prompt(batch)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            results = parse_json_response(response.content[0].text)
            for r in results:
                tema = r["tema"]
                if tema not in TEMAS_VALIDOS:
                    tema = "geral"
                tema_map[int(r["id"])] = tema
            print(f"OK ({len(results)} classified)")
        except Exception as e:
            print(f"Error: {e}")

    for item in items:
        item["tema"] = tema_map.get(item["id"], "geral")

    print(f"  Total: {len(tema_map)} classified\n")

    # Step 4: Import to DB
    print("--- Step 4: Importing to database ---")

    async def import_to_db():
        async with async_session() as db:
            updated = 0
            for item in items:
                resumo = item.get("resumo_cidadao", "").strip()
                if not resumo:
                    continue
                descricao = item.get("descricao_detalhada", "").strip()
                tema = item.get("tema", "geral")

                await db.execute(
                    text("""
                        UPDATE proposicoes
                        SET resumo_cidadao = :resumo,
                            descricao_detalhada = :descricao,
                            tema = :tema
                        WHERE id = :id
                    """),
                    {"resumo": resumo, "descricao": descricao, "tema": tema, "id": item["id"]},
                )
                updated += 1
            await db.commit()
            print(f"  Updated {updated} proposições in DB")

    asyncio.run(import_to_db())

    # Save JSON backup
    output_file = "/tmp/proposicoes_restantes_processadas.json"
    with open(output_file, "w") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"  Backup saved to {output_file}")

    print(f"\n=== Done! ===")


if __name__ == "__main__":
    main()
