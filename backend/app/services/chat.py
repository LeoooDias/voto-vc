"""Chat service for proposição Q&A using Claude Haiku 4.5."""

import json
import logging
import re
from collections.abc import AsyncGenerator

import anthropic
import httpx

from app.config import settings
from app.models.proposicao import Proposicao

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


MODEL = "claude-haiku-4-5-20251001"
MAX_HISTORY = 20
MAX_TOOL_ROUNDS = 3


def build_system_prompt(prop: Proposicao) -> str:
    parts = [
        "Você é um assistente especializado em legislação brasileira.",
        "Responda perguntas sobre a proposição abaixo de forma clara, objetiva e em português.",
        "Use as informações fornecidas como contexto principal.",
        "Se precisar de mais detalhes sobre o texto completo, "
        "use a ferramenta buscar_inteiro_teor.",
        "Se precisar de informações adicionais, use web_search.",
        "Seja neutro e imparcial — apresente fatos, não opiniões.",
        "Se não souber a resposta, diga isso em vez de inventar.",
        "",
        f"=== PROPOSIÇÃO: {prop.tipo} {prop.numero}/{prop.ano} ===",
        f"Ementa: {prop.ementa}",
    ]
    if prop.resumo_cidadao:
        parts.append(f"\nResumo cidadão: {prop.resumo_cidadao}")
    if prop.descricao_detalhada:
        parts.append(f"\nDescrição detalhada: {prop.descricao_detalhada}")
    if prop.situacao:
        parts.append(f"\nSituação: {prop.situacao}")
    if prop.url_inteiro_teor:
        parts.append(f"\nURL do inteiro teor: {prop.url_inteiro_teor}")

    # Include raw data summary if available
    if prop.dados_brutos and isinstance(prop.dados_brutos, dict):
        keywords = prop.dados_brutos.get("keywords", "")
        if keywords:
            parts.append(f"\nPalavras-chave: {keywords}")

    return "\n".join(parts)


TOOLS = [
    {
        "name": "buscar_inteiro_teor",
        "description": (
            "Busca o texto completo (inteiro teor) da proposição "
            "a partir da URL oficial. Use quando o usuário perguntar "
            "sobre detalhes específicos, artigos ou incisos."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Busca informações na web sobre a proposição ou temas relacionados. "
            "Use quando precisar de contexto adicional, notícias recentes, "
            "opiniões de especialistas ou informações não contidas no texto da proposição."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Termo de busca em português",
                }
            },
            "required": ["query"],
        },
    },
]


async def _fetch_inteiro_teor(url: str) -> str:
    """Fetch the full text from the proposição URL."""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "pdf" in content_type:
                return (
                    "(O inteiro teor está em formato PDF. "
                    "Use web_search para encontrar análises do texto.)"
                )
            text = resp.text
            # Truncate very long documents
            if len(text) > 50000:
                text = text[:50000] + "\n\n[... texto truncado por tamanho ...]"
            return text
    except Exception as e:
        logger.warning(f"Failed to fetch inteiro teor from {url}: {e}")
        return f"(Erro ao buscar inteiro teor: {e})"


async def _web_search(query: str) -> str:
    """Simple web search via DuckDuckGo HTML."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (compatible; voto.vc bot)"},
            )
            resp.raise_for_status()
            # Extract text snippets from results (basic parsing)
            text = resp.text
            results = []
            # Find result snippets between <a class="result__snippet"> tags
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', text, re.DOTALL)
            titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', text, re.DOTALL)
            urls = re.findall(r'class="result__url"[^>]*>(.*?)</a>', text, re.DOTALL)
            for i, snippet in enumerate(snippets[:5]):
                clean = re.sub(r"<[^>]+>", "", snippet).strip()
                title = re.sub(r"<[^>]+>", "", titles[i]).strip() if i < len(titles) else ""
                url = re.sub(r"<[^>]+>", "", urls[i]).strip() if i < len(urls) else ""
                if clean:
                    results.append(f"**{title}** ({url})\n{clean}")
            if results:
                return "\n\n".join(results)
            return "(Nenhum resultado encontrado.)"
    except Exception as e:
        logger.warning(f"Web search failed for '{query}': {e}")
        return f"(Erro na busca: {e})"


async def _execute_tool(tool_name: str, tool_input: dict, prop: Proposicao) -> str:
    if tool_name == "buscar_inteiro_teor":
        if prop.url_inteiro_teor:
            return await _fetch_inteiro_teor(prop.url_inteiro_teor)
        return "(Esta proposição não tem URL de inteiro teor cadastrada.)"
    elif tool_name == "web_search":
        query = tool_input.get("query", f"{prop.tipo} {prop.numero}/{prop.ano}")
        return await _web_search(query)
    return "(Ferramenta desconhecida.)"


async def stream_chat(
    prop: Proposicao,
    message: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    """Stream chat response, handling tool calls transparently.

    Yields text chunks as they arrive. Tool calls are resolved server-side
    and re-submitted; the caller only sees final text output.
    """
    client = _get_client()
    system = build_system_prompt(prop)

    # Build messages from history + new message
    messages: list[dict] = []
    for h in history[-MAX_HISTORY:]:
        if h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    for _round in range(MAX_TOOL_ROUNDS + 1):
        # Try streaming first
        collected_text = ""
        tool_uses: list[dict] = []

        async with client.messages.stream(
            model=MODEL,
            max_tokens=2048,
            system=system,
            messages=messages,
            tools=TOOLS,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        tool_uses.append(
                            {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "input_json": "",
                            }
                        )
                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        yield event.delta.text
                        collected_text += event.delta.text
                    elif event.delta.type == "input_json_delta":
                        if tool_uses:
                            tool_uses[-1]["input_json"] += event.delta.partial_json

            response = await stream.get_final_message()

        # If no tool use, we're done
        if response.stop_reason != "tool_use" or not tool_uses:
            break

        # Handle tool calls: build assistant message with all content blocks, then tool results
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        messages.append({"role": "assistant", "content": assistant_content})

        # Execute tools and add results
        tool_results = []
        for tool in tool_uses:
            try:
                tool_input = json.loads(tool["input_json"]) if tool["input_json"] else {}
            except json.JSONDecodeError:
                tool_input = {}
            result_text = await _execute_tool(tool["name"], tool_input, prop)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool["id"],
                    "content": result_text,
                }
            )

        messages.append({"role": "user", "content": tool_results})
