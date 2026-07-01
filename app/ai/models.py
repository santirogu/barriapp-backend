"""AI assistant models: RAG knowledge base and conversations. See DATA_MODEL §3.13-3.14."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field
from pymongo import IndexModel


class KnowledgeSourceType(StrEnum):
    FAQ = "faq"
    POLICY = "policy"
    STORE = "store"
    PRODUCT = "product"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AiKnowledge(Document):
    source_type: KnowledgeSourceType
    ref_id: PydanticObjectId | None = None
    content: str
    embedding: list[float] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "ai_knowledge"
        # NOTE: production uses an Atlas Vector Search index on `embedding`
        # ($vectorSearch). Local/community Mongo can't host it, so retrieval falls
        # back to in-app cosine ranking (see app/ai/retrieval.py).
        indexes = [  # noqa: RUF012
            IndexModel("source_type"),
        ]


class ConversationMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    at: datetime = Field(default_factory=_utcnow)


class AiConversation(Document):
    user_id: PydanticObjectId
    messages: list[ConversationMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)

    class Settings:
        name = "ai_conversations"
        indexes = [  # noqa: RUF012
            IndexModel([("user_id", 1), ("created_at", -1)]),
        ]
