"""Chat service for proposição Q&A using Claude Sonnet 4.5."""

import io
import json
import logging
import re
from collections.abc import AsyncGenerator

import anthropic
import httpx
import pdfplumber

from app.config import settings
from app.models.proposicao import Proposicao

logger = logging.getLogger(__name__)

# Simple in-memory cache for extracted PDF text (URL -> text)
_inteiro_teor_cache: dict[str, str] = {}

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


MODEL = "claude-sonnet-4-6"
MAX_HISTORY = 20
MAX_TOOL_ROUNDS = 3


def build_system_prompt(prop: Proposicao) -> str:
    parts = [
        "Você é um assistente especializado em legislação brasileira no site voto.vc.",
        "Seu papel é ajudar cidadãos a entender proposições legislativas "
        "de forma clara e acessível.",
        "",
        "REGRAS:",
        "- Responda SEMPRE com base nas informações fornecidas abaixo sobre a proposição.",
        "- Você tem conhecimento amplo sobre política e legislação brasileira — USE-O.",
        "- Analise a proposição com profundidade: contexto histórico, impactos, argumentos.",
        "- NÃO diga 'não tenho informações' se a ementa/resumo/descrição já contém o suficiente.",
        "- Só use ferramentas quando REALMENTE precisar de dados que não possui.",
        "- Seja direto. Nada de 'vou buscar' ou 'deixe-me tentar'. Responda ou use a ferramenta.",
        "- Seja neutro e imparcial — apresente múltiplos lados.",
        "- Use markdown: **negrito**, listas, etc.",
        "- Respostas concisas mas completas. Máximo ~300 palavras.",
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

    if prop.dados_brutos and isinstance(prop.dados_brutos, dict):
        keywords = prop.dados_brutos.get("keywords", "")
        if keywords:
            parts.append(f"\nPalavras-chave: {keywords}")

    return "\n".join(parts)


TOOLS = [
    {
        "name": "buscar_inteiro_teor",
        "description": (
            "Busca o texto completo (inteiro teor) da proposição a partir da URL oficial. "
            "Use APENAS quando o usuário perguntar sobre artigos, incisos ou detalhes "
            "específicos do texto legal que não estão no resumo."
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
            "Busca informações na web. Use APENAS quando precisar de dados factuais "
            "específicos não contidos na proposição (ex: estatísticas, notícias recentes, "
            "posições de entidades). NÃO use para perguntas que podem ser respondidas "
            "com análise do conteúdo já fornecido."
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


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pdfplumber."""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)


async def _fetch_inteiro_teor(url: str) -> str:
    """Fetch and extract text from the proposição URL (PDF or HTML)."""
    # Check cache first
    if url in _inteiro_teor_cache:
        return _inteiro_teor_cache[url]

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")

            if "pdf" in content_type:
                text = _extract_pdf_text(resp.content)
                if not text.strip():
                    return "(PDF sem texto extraível — pode ser imagem escaneada.)"
            else:
                text = resp.text
                text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
                text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()

            if len(text) > 30000:
                text = text[:30000] + "\n\n[... texto truncado ...]"

            _inteiro_teor_cache[url] = text
            return text
    except Exception as e:
        logger.warning(f"Failed to fetch inteiro teor from {url}: {e}")
        return (
            "(Não foi possível acessar o inteiro teor. "
            "Responda com base nas informações disponíveis.)"
        )


async def _web_search(query: str) -> str:
    """Web search via DuckDuckGo HTML."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            )
            resp.raise_for_status()
            text = resp.text
            results = []
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', text, re.DOTALL)
            titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', text, re.DOTALL)
            for i, snippet in enumerate(snippets[:5]):
                clean = re.sub(r"<[^>]+>", "", snippet).strip()
                title = re.sub(r"<[^>]+>", "", titles[i]).strip() if i < len(titles) else ""
                if clean:
                    results.append(f"**{title}**\n{clean}")
            if results:
                return "\n\n".join(results)
            return (
                "(Busca não retornou resultados. "
                "Responda com base nas informações já disponíveis e seu conhecimento.)"
            )
    except Exception as e:
        logger.warning(f"Web search failed for '{query}': {e}")
        return (
            "(Busca indisponível. "
            "Responda com base nas informações já disponíveis e seu conhecimento.)"
        )


def build_posicao_system_prompt(
    posicao: object,
    proposicoes: list[dict],
) -> str:
    """Build system prompt for position-level chat."""
    parts = [
        "Você é um assistente especializado em legislação brasileira no site voto.vc.",
        "Seu papel é ajudar cidadãos a entender posições temáticas e as proposições "
        "legislativas relacionadas de forma clara e acessível.",
        "",
        "REGRAS:",
        "- Responda com base nas informações fornecidas sobre a posição e suas proposições.",
        "- Você tem conhecimento amplo sobre política e legislação brasileira — USE-O.",
        "- Explique como cada proposição se relaciona com a posição temática.",
        "- Seja neutro e imparcial — apresente múltiplos lados.",
        "- Use markdown: **negrito**, listas, etc.",
        "- Respostas concisas mas completas. Máximo ~300 palavras.",
        "",
        f"=== POSIÇÃO TEMÁTICA: {posicao.titulo} ===",
        f"Descrição: {posicao.descricao}",
        f"Tema: {posicao.tema}",
        "",
        "=== PROPOSIÇÕES RELACIONADAS ===",
    ]
    for p in proposicoes:
        direcao_label = (
            "votar SIM nesta proposição apoia esta posição"
            if p["direcao"] == "sim"
            else "votar NÃO nesta proposição apoia esta posição"
        )
        entry = f"- {p['tipo']} {p['numero']}/{p['ano']}: {p.get('ementa', '(sem ementa)')}"
        entry += f"\n  Direção: {direcao_label}"
        if p.get("resumo_cidadao"):
            entry += f"\n  Resumo: {p['resumo_cidadao']}"
        parts.append(entry)

    return "\n".join(parts)


POSICAO_TOOLS = [
    {
        "name": "web_search",
        "description": (
            "Busca informações na web. Use APENAS quando precisar de dados factuais "
            "específicos não contidos nas proposições (ex: estatísticas, notícias recentes, "
            "posições de entidades). NÃO use para perguntas que podem ser respondidas "
            "com análise do conteúdo já fornecido."
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


async def _execute_posicao_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "web_search":
        query = tool_input.get("query", "")
        return await _web_search(query)
    return "(Ferramenta desconhecida.)"


async def _execute_tool(tool_name: str, tool_input: dict, prop: Proposicao) -> str:
    if tool_name == "buscar_inteiro_teor":
        if prop.url_inteiro_teor:
            return await _fetch_inteiro_teor(prop.url_inteiro_teor)
        return "(Esta proposição não tem URL de inteiro teor. Use as informações disponíveis.)"
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

    messages: list[dict] = []
    for h in history[-MAX_HISTORY:]:
        if h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    for _round in range(MAX_TOOL_ROUNDS + 1):
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

        if response.stop_reason != "tool_use" or not tool_uses:
            break

        # Handle tool calls
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


async def stream_posicao_chat(
    posicao: object,
    proposicoes: list[dict],
    message: str,
    history: list[dict],
) -> AsyncGenerator[str, None]:
    """Stream chat response for a thematic position.

    Similar to stream_chat but uses position-specific system prompt and tools.
    """
    client = _get_client()
    system = build_posicao_system_prompt(posicao, proposicoes)

    messages: list[dict] = []
    for h in history[-MAX_HISTORY:]:
        if h.get("role") in ("user", "assistant"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    for _round in range(MAX_TOOL_ROUNDS + 1):
        collected_text = ""
        tool_uses: list[dict] = []

        async with client.messages.stream(
            model=MODEL,
            max_tokens=2048,
            system=system,
            messages=messages,
            tools=POSICAO_TOOLS,
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

        if response.stop_reason != "tool_use" or not tool_uses:
            break

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

        tool_results = []
        for tool in tool_uses:
            try:
                tool_input = json.loads(tool["input_json"]) if tool["input_json"] else {}
            except json.JSONDecodeError:
                tool_input = {}
            result_text = await _execute_posicao_tool(tool["name"], tool_input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool["id"],
                    "content": result_text,
                }
            )

        messages.append({"role": "user", "content": tool_results})
