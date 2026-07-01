"""Agentic LLM answer generation with tool-calling.

Grounded RAG + tools: the assistant can call backend tools (order status, store
search) to answer with live data. With ``ANTHROPIC_API_KEY`` we run Claude's
tool-use loop; otherwise a deterministic planner (``select_tool``) picks at most one
tool and a fallback composes the answer — keeping the feature usable and hermetic
in tests. User-facing text is Spanish.
"""

from dataclasses import dataclass, field

import structlog

from app.ai.tools import Tool, ToolContext, select_tool
from app.core.config import get_settings

logger = structlog.get_logger()

SYSTEM_PROMPT = (
    "Eres el asistente de BarriApp, una app de domicilios para tiendas de barrio en "
    "Colombia. Responde de forma breve y clara en español. Usa las herramientas "
    "disponibles para datos en vivo (estado de pedidos, tiendas) y el contexto "
    "provisto. Si no tienes información suficiente, dilo y sugiere contactar soporte."
)

_NO_CONTEXT = (
    "Por ahora no tengo información suficiente para responder eso. "
    "¿Puedes reformular tu pregunta o contactar a soporte?"
)

_MAX_TOOL_ITERATIONS = 4


@dataclass
class AgentResult:
    answer: str
    tools_used: list[str] = field(default_factory=list)


def compose_fallback(contexts: list[str]) -> str:
    """Deterministic, offline answer used when no LLM provider is configured."""
    if not contexts:
        return _NO_CONTEXT
    return f"Según la información de BarriApp: {contexts[0].strip()}"


async def _fallback_agent(
    message: str, contexts: list[str], tools: list[Tool], ctx: ToolContext
) -> AgentResult:
    tools_used: list[str] = []
    ctx_list = list(contexts)
    name = select_tool(message, [t.name for t in tools])
    if name is not None:
        tool = next(t for t in tools if t.name == name)
        result = await tool.run(ctx, {})
        ctx_list.insert(0, result)  # freshest, most relevant context first
        tools_used.append(name)
    return AgentResult(answer=compose_fallback(ctx_list), tools_used=tools_used)


async def _claude_agent(
    message: str, contexts: list[str], tools: list[Tool], ctx: ToolContext, model: str, api_key: str
) -> AgentResult:
    from anthropic import AsyncAnthropic  # lazy import; optional dependency

    client = AsyncAnthropic(api_key=api_key)
    anthropic_tools = [
        {"name": t.name, "description": t.description, "input_schema": t.input_schema}
        for t in tools
    ]
    by_name = {t.name: t for t in tools}
    context_block = "\n\n".join(f"- {c}" for c in contexts) or "(sin contexto)"
    messages: list[dict[str, object]] = [
        {"role": "user", "content": f"Contexto:\n{context_block}\n\nPregunta: {message}"}
    ]
    tools_used: list[str] = []

    for _ in range(_MAX_TOOL_ITERATIONS):
        resp = await client.messages.create(
            model=model,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            tools=anthropic_tools,
            messages=messages,
        )
        if resp.stop_reason != "tool_use":
            text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
            return AgentResult(answer=text or _NO_CONTEXT, tools_used=tools_used)

        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if block.type == "tool_use":
                tool = by_name.get(block.name)
                output = (
                    await tool.run(ctx, dict(block.input)) if tool else "Herramienta no disponible."
                )
                tools_used.append(block.name)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        messages.append({"role": "user", "content": results})

    return AgentResult(answer=_NO_CONTEXT, tools_used=tools_used)


async def run_agent(
    message: str, contexts: list[str], tools: list[Tool], ctx: ToolContext
) -> AgentResult:
    settings = get_settings()
    if settings.anthropic_api_key:
        try:
            return await _claude_agent(
                message, contexts, tools, ctx, settings.ai_model, settings.anthropic_api_key
            )
        except Exception:
            logger.exception("claude_agent_failed_falling_back")
    return await _fallback_agent(message, contexts, tools, ctx)
