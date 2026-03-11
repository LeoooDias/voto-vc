"""Use Claude API to generate citizen-friendly summaries of proposições."""
import asyncio
import json
import os
import sys

import anthropic

INPUT_FILE = "/tmp/proposicoes_divisivas.json"
OUTPUT_FILE = "/tmp/proposicoes_resumidas.json"
BATCH_SIZE = 10  # proposições per API call


def build_prompt(items: list[dict]) -> str:
    lines = []
    for item in items:
        lines.append(
            f"ID:{item['id']} | {item['tipo']} {item['numero']}/{item['ano']} | "
            f"Sim:{item['sim']} Não:{item['nao']} | "
            f"Ementa: {item['ementa']}"
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


def summarize_batch(client: anthropic.Anthropic, items: list[dict]) -> list[dict]:
    prompt = build_prompt(items)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Extract JSON from response
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

    # Load existing results to resume
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            for item in json.load(f):
                existing[item["id"]] = item

    client = anthropic.Anthropic(api_key=api_key)
    results = list(existing.values())

    remaining = [item for item in items if item["id"] not in existing]
    print(f"Total: {len(items)}, already done: {len(existing)}, remaining: {len(remaining)}")

    for i in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[i : i + BATCH_SIZE]
        print(f"Processing batch {i // BATCH_SIZE + 1} ({len(batch)} items)...")

        try:
            summaries = summarize_batch(client, batch)
            summary_map = {int(s["id"]): s["resumo"] for s in summaries}

            for item in batch:
                result = {**item, "resumo_cidadao": summary_map.get(item["id"], "")}
                results.append(result)
                existing[item["id"]] = result

            # Save after each batch
            with open(OUTPUT_FILE, "w") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            print(f"  Done, {len(results)} total saved")
        except Exception as e:
            print(f"  Error: {e}")
            continue

    print(f"\nCompleted! {len(results)} proposições saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
