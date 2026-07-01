"""Pure retrieval helpers (no DB): cosine similarity + top-k ranking.

MVP ranks in-app; at scale this is replaced by Atlas ``$vectorSearch``.
"""

import math


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def rank(
    query: list[float], items: list[tuple[str, list[float], str]], *, top_k: int
) -> list[tuple[str, float, str]]:
    """Rank (id, embedding, content) items by cosine similarity to the query.

    Returns the top_k as (id, score, content), highest score first.
    """
    scored = [(item_id, cosine_similarity(query, emb), content) for item_id, emb, content in items]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
