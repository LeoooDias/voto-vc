"""Enrich proposições with detailed descriptions using web search + Claude API."""
import asyncio
import json
import os
import sys
import time

import anthropic
import httpx

INPUT_FILE = "/tmp/proposicoes_resumidas.json"
OUTPUT_FILE = "/tmp/proposicoes_enriquecidas.json"


def search_web(query: str) -> str:
    """Search using DuckDuckGo HTML and extract text snippets."""
    try:
        r = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        # Extract text snippets from result snippets
        text = r.text
        snippets = []
        for marker in ['class="result__snippet">', 'class="result__title"']:
            parts = text.split(marker)
            for part in parts[1:6]:  # up to 5 results
                end = part.find("</")
                if end > 0:
                    snippet = part[:end].replace("<b>", "").replace("</b>", "").strip()
                    if snippet:
                        snippets.append(snippet)
        return "\n".join(snippets[:8])
    except Exception as e:
        return f"(search failed: {e})"


def build_prompt(item: dict, web_context: str) -> str:
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
Ementa oficial: {item['ementa']}

Contexto da web sobre esta proposição:
{web_context}

Responda APENAS com o texto da descrição, sem aspas nem formatação."""


def enrich_item(client: anthropic.Anthropic, item: dict) -> str:
    query = f"{item['tipo']} {item['numero']}/{item['ano']} câmara deputados"
    web_context = search_web(query)

    prompt = build_prompt(item, web_context)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    with open(INPUT_FILE) as f:
        items = json.load(f)

    # Load existing results to resume
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            for item in json.load(f):
                if item.get("descricao_detalhada"):
                    existing[item["id"]] = item

    client = anthropic.Anthropic(api_key=api_key)
    results = list(existing.values())

    remaining = [item for item in items if item["id"] not in existing]
    print(f"Total: {len(items)}, already done: {len(existing)}, remaining: {len(remaining)}")

    for i, item in enumerate(remaining):
        label = f"{item['tipo']} {item['numero']}/{item['ano']}"
        print(f"[{i+1}/{len(remaining)}] {label}...", end=" ", flush=True)

        try:
            descricao = enrich_item(client, item)
            result = {**item, "descricao_detalhada": descricao}
            results.append(result)
            existing[item["id"]] = result

            # Save after each item
            with open(OUTPUT_FILE, "w") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            print(f"OK ({len(descricao)} chars)")
            time.sleep(0.5)  # gentle rate limiting
        except Exception as e:
            print(f"Error: {e}")
            continue

    print(f"\nCompleted! {len(results)} proposições saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
