"""AI assistant I/O schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.ai.models import (
    AiConversation,
    AiKnowledge,
    ConversationMessage,
    KnowledgeSourceType,
)


class KnowledgeIngest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    source_type: KnowledgeSourceType = KnowledgeSourceType.FAQ
    metadata: dict[str, str] = Field(default_factory=dict)


class KnowledgePublic(BaseModel):
    id: str
    source_type: KnowledgeSourceType
    content: str

    @classmethod
    def from_knowledge(cls, k: AiKnowledge) -> "KnowledgePublic":
        return cls(id=str(k.id), source_type=k.source_type, content=k.content)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None
    order_id: str | None = None  # optional grounding: include this order's status


class SourceRef(BaseModel):
    id: str
    source_type: KnowledgeSourceType
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    sources: list[SourceRef]


class ConversationPublic(BaseModel):
    id: str
    messages: list[ConversationMessage]
    created_at: datetime

    @classmethod
    def from_conversation(cls, c: AiConversation) -> "ConversationPublic":
        return cls(id=str(c.id), messages=c.messages, created_at=c.created_at)
