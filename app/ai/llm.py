"""LLM answer generation.

Grounded RAG: the model answers from retrieved context only. When
``ANTHROPIC_API_KEY`` is configured we call Claude; otherwise a deterministic
fallback composes an answer from the top context (keeps the endpoint usable and
tests offline). User-facing text is Spanish.
"""

import structlog

from app.core.config import get_settings

logger = structlog.get_logger()

SYSTEM_PROMPT = (
    "Eres el asistente de BarriApp, una app de domicilios para tiendas de barrio en "
    "Colombia. Responde de forma breve y clara, SOLO con la información de contexto "
    "provista. Si no tienes suficiente información, dilo y sugiere contactar soporte."
)

_NO_CONTEXT = (
    "Por ahora no tengo información suficiente para responder eso. "
    "¿Puedes reformular tu pregunta o contactar a soporte?"
)


def compose_fallback(contexts: list[str]) -> str:
    """Deterministic, offline answer used when no LLM provider is configured."""
    if not contexts:
        return _NO_CONTEXT
    return f"Según la información de BarriApp: {contexts[0].strip()}"


async def _claude_answer(message: str, contexts: list[str], model: str, api_key: str) -> str:
    from anthropic import AsyncAnthropic  # lazy import; optional dependency

    client = AsyncAnthropic(api_key=api_key)
    context_block = "\n\n".join(f"- {c}" for c in contexts) or "(sin contexto)"
    response = await client.messages.create(
        model=model,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Contexto:\n{context_block}\n\nPregunta: {message}"}
        ],
    )
    parts = [block.text for block in response.content if block.type == "text"]
    return "\n".join(parts).strip() or _NO_CONTEXT


async def answer(message: str, contexts: list[str]) -> str:
    settings = get_settings()
    if settings.anthropic_api_key:
        try:
            return await _claude_answer(
                message, contexts, settings.ai_model, settings.anthropic_api_key
            )
        except Exception:
            logger.exception("claude_answer_failed_falling_back")
    return compose_fallback(contexts)
