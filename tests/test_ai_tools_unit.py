"""Unit tests for the offline tool planner (pure, no DB)."""

import pytest

from app.ai.tools import select_tool

_NAMES = ["get_order_status", "search_stores"]


@pytest.mark.req("AI-3")
def test_select_order_tool_on_status_intent() -> None:
    assert select_tool("¿Dónde está mi pedido?", _NAMES) == "get_order_status"
    assert select_tool("quiero el estado de mi orden", _NAMES) == "get_order_status"


@pytest.mark.req("AI-3")
def test_payment_question_does_not_trigger_order_tool() -> None:
    # mentions "pedido" but has no status/location intent → no tool (RAG answers it)
    assert select_tool("¿Cómo puedo pagar mi pedido?", _NAMES) is None


@pytest.mark.req("AI-3")
def test_select_store_tool_and_none() -> None:
    assert select_tool("¿Qué tiendas hay cerca?", _NAMES) == "search_stores"
    assert select_tool("hola, buenos días", _NAMES) is None
