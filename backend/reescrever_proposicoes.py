"""Rewrite proposição titles and descriptions using Claude Opus 4.6.

For each proposição in the questionnaire pool:
- resumo_cidadao: popular common name (e.g., "Lei das Bets", "PEC da Segurança Pública")
- descricao_detalhada: clear, detailed explanation of WHAT changes, WHO benefits, practical impact

Uses web search for context on each proposição.

Usage:
    ANTHROPIC_API_KEY=sk-... python reescrever_proposicoes.py [--start-from ID] [--only-raw] [--limit N]

Input:  /tmp/proposicoes_para_reescrita.json (exported from production DB)
Output: /tmp/proposicoes_reescritas.json (incremental, resumable)
"""

import argparse
import json
import os
import sys
import time

import anthropic
import httpx

INPUT_FILE = "/tmp/proposicoes_para_reescrita.json"
OUTPUT_FILE = "/tmp/proposicoes_reescritas.json"

SYSTEM_PROMPT = """Você é um especialista em comunicação política brasileira. Sua missão é traduzir legislação para linguagem que qualquer cidadão brasileiro entenda — simples, clara, direta, sem jargão.

Você recebe proposições legislativas e deve gerar:

1. **titulo** — O nome popular pelo qual o projeto é (ou deveria ser) conhecido. Curto, memorável, descritivo.
   - NUNCA use a nomenclatura técnica como título (não "PL 1234/2025" nem "Altera a Lei nº...")
   - Use o nome popular se existir (ex: "Lei das Bets", "PEC da Segurança Pública", "Marco do Saneamento")
   - Se não houver nome popular consagrado, crie um descritivo (ex: "Quebra de Patente de Remédios", "Imposto de Renda Mais Justo")
   - Máximo 60 caracteres
   - Comece com substantivo ou verbo no infinitivo quando apropriado

2. **descricao** — Explicação clara e detalhada do que a proposição faz na prática.
   - 3-5 frases, máximo 500 caracteres
   - Explique O QUE muda concretamente (valores, prazos, regras novas)
   - Diga QUEM é afetado e COMO
   - Mencione o impacto prático na vida real
   - Use linguagem obsessivamente simples — como se explicasse para alguém que nunca acompanhou política
   - Seja neutro — não tome posição a favor ou contra
   - NÃO cite artigos de lei, números de lei, ou jargão jurídico
   - NÃO repita o título na descrição

Responda APENAS em JSON válido: {"titulo": "...", "descricao": "..."}"""


def search_web(query: str) -> str:
    """Search DuckDuckGo for context about a proposição."""
    try:
        r = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (compatible; votovc/1.0)"},
            timeout=10,
        )
        snippets = []
        for marker in ['class="result__snippet">', 'class="result__title">']:
            parts = r.text.split(marker)
            for part in parts[1:6]:
                end = part.find("</")
                if end > 0:
                    snippet = (
                        part[:end]
                        .replace("<b>", "")
                        .replace("</b>", "")
                        .replace("&amp;", "&")
                        .replace("&quot;", '"')
                        .strip()
                    )
                    if snippet and len(snippet) > 20:
                        snippets.append(snippet)
        return "\n".join(snippets[:8]) if snippets else "(sem resultados)"
    except Exception as e:
        return f"(busca falhou: {e})"


def build_user_prompt(item: dict, web_context: str) -> str:
    parts = [
        f"Proposição: {item['tipo']} {item['numero']}/{item['ano']}",
        f"Tema: {item.get('tema') or 'geral'}",
        f"Ementa oficial: {item['ementa']}",
    ]

    # Include existing content for review/improvement
    if item.get("has_custom") and item.get("resumo_cidadao"):
        parts.append(f"Título atual (pode melhorar se necessário): {item['resumo_cidadao']}")
    if item.get("descricao_detalhada"):
        parts.append(
            f"Descrição atual (melhore se possível): {item['descricao_detalhada']}"
        )

    # Casa info
    casas = item.get("casas", [])
    if casas:
        casas_str = " e ".join(c.title() for c in sorted(casas))
        parts.append(f"Votada em: {casas_str}")

    parts.append(f"\nContexto da web:\n{web_context}")

    return "\n".join(parts)


def rewrite_item(client: anthropic.Anthropic, item: dict) -> dict:
    """Call Claude Opus 4.6 to rewrite a single proposição."""
    query = f'"{item["tipo"]} {item["numero"]}/{item["ano"]}" brasil legislação'
    web_context = search_web(query)

    user_prompt = build_user_prompt(item, web_context)

    response = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = response.content[0].text.strip()

    # Extract JSON
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]

    result = json.loads(text)
    return {
        "titulo": result["titulo"],
        "descricao": result["descricao"],
    }


def main():
    parser = argparse.ArgumentParser(description="Rewrite proposição content with Claude Opus 4.6")
    parser.add_argument("--start-from", type=int, default=0, help="Start from this proposição ID")
    parser.add_argument("--only-raw", action="store_true", help="Only process items with resumo = ementa")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of items to process")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without calling API")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not args.dry_run:
        print("Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    with open(INPUT_FILE) as f:
        items = json.load(f)

    # Load existing results
    existing = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            for item in json.load(f):
                existing[item["id"]] = item

    # Filter items
    to_process = []
    for item in items:
        if item["id"] in existing:
            continue
        if args.start_from and item["id"] < args.start_from:
            continue
        if args.only_raw and item.get("has_custom"):
            continue
        to_process.append(item)

    if args.limit:
        to_process = to_process[:args.limit]

    total = len(items)
    done = len(existing)
    remaining = len(to_process)
    print(f"Total: {total}, já processados: {done}, a processar: {remaining}")

    if args.dry_run:
        for item in to_process[:10]:
            status = "RAW" if not item.get("has_custom") else "CUSTOM"
            print(f"  [{status}] {item['tipo']} {item['numero']}/{item['ano']} (id={item['id']}): {item['ementa'][:80]}")
        if remaining > 10:
            print(f"  ... e mais {remaining - 10}")
        return

    client = anthropic.Anthropic(api_key=api_key)
    results = list(existing.values())

    for i, item in enumerate(to_process):
        label = f"{item['tipo']} {item['numero']}/{item['ano']}"
        status = "RAW" if not item.get("has_custom") else "IMPROVE"
        print(f"[{done + i + 1}/{total}] [{status}] {label}...", end=" ", flush=True)

        try:
            rewritten = rewrite_item(client, item)
            result = {
                **item,
                "novo_titulo": rewritten["titulo"],
                "nova_descricao": rewritten["descricao"],
            }
            results.append(result)
            existing[item["id"]] = result

            # Save after each item
            with open(OUTPUT_FILE, "w") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            print(f"✓ {rewritten['titulo'][:50]}")
            time.sleep(0.3)
        except json.JSONDecodeError as e:
            print(f"JSON error: {e}")
            continue
        except anthropic.RateLimitError:
            print("Rate limited, waiting 60s...")
            time.sleep(60)
            # Retry
            try:
                rewritten = rewrite_item(client, item)
                result = {**item, "novo_titulo": rewritten["titulo"], "nova_descricao": rewritten["descricao"]}
                results.append(result)
                existing[item["id"]] = result
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"✓ (retry) {rewritten['titulo'][:50]}")
            except Exception as e2:
                print(f"Retry failed: {e2}")
                continue
        except Exception as e:
            print(f"Error: {e}")
            continue

    print(f"\nCompleto! {len(results)} proposições salvas em {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
