"""Unit tests for the RAG building blocks (no DB, no external calls)."""

import math

import pytest

from app.ai.embeddings import embed
from app.ai.llm import compose_fallback
from app.ai.retrieval import cosine_similarity, rank


@pytest.mark.req("AI-2")
def test_embed_is_deterministic_and_normalized() -> None:
    assert embed("hola mundo") == embed("hola mundo")
    assert embed("hola mundo") != embed("otra cosa distinta")
    norm = math.sqrt(sum(x * x for x in embed("pago en efectivo")))
    assert abs(norm - 1.0) < 1e-9


@pytest.mark.req("AI-2")
def test_cosine_similarity() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


@pytest.mark.req("AI-2")
def test_rank_orders_by_similarity_to_query() -> None:
    items = [
        ("pay", embed("puedes pagar en efectivo o con wompi"), "pagos"),
        ("hours", embed("horarios de atencion de la tienda"), "horarios"),
    ]
    ranked = rank(embed("como puedo pagar"), items, top_k=1)
    assert ranked[0][0] == "pay"  # the payment doc wins


@pytest.mark.req("AI-2")
def test_compose_fallback() -> None:
    assert compose_fallback(["Pagas con Wompi"]).startswith("Según la información")
    assert "Wompi" in compose_fallback(["Pagas con Wompi"])
    assert "no tengo información" in compose_fallback([]).lower()
