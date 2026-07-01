"""Text embeddings.

MVP uses a deterministic, dependency-free hashing embedding (bag-of-tokens over a
fixed dimension) so retrieval works offline and in tests. Production can swap this
for a real embedding model (e.g. Voyage/OpenAI) behind the same ``embed`` function.
"""

import hashlib
import math
import re

EMBEDDING_DIM = 256
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def embed(text: str) -> list[float]:
    """Return a deterministic, L2-normalized embedding for ``text``."""
    vec = [0.0] * EMBEDDING_DIM
    for token in _tokens(text):
        digest = hashlib.md5(token.encode(), usedforsecurity=False).hexdigest()
        vec[int(digest, 16) % EMBEDDING_DIM] += 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]
