"""AI assistant business logic: knowledge ingestion and grounded RAG chat."""

from beanie import PydanticObjectId
from fastapi import status

from app.ai import embeddings, llm, retrieval
from app.ai import repository as ai_repo
from app.ai.models import AiConversation, AiKnowledge, ConversationMessage
from app.ai.schemas import ChatRequest, ChatResponse, KnowledgeIngest, SourceRef
from app.audit import service as audit
from app.audit.models import AuditModule
from app.core.config import get_settings
from app.core.errors import AppError
from app.orders import repository as orders_repo
from app.users.models import User
from app.users.service import primary_role

_SNIPPET_LEN = 200


async def ingest_knowledge(admin: User, data: KnowledgeIngest) -> AiKnowledge:
    knowledge = AiKnowledge(
        source_type=data.source_type,
        content=data.content,
        embedding=embeddings.embed(data.content),
        metadata=data.metadata,
    )
    await ai_repo.insert_knowledge(knowledge)
    await audit.record(
        module=AuditModule.AI,
        action="ai.knowledge.created",
        actor_id=admin.id,
        actor_role=primary_role(admin),
        target_type="ai_knowledge",
        target_id=knowledge.id,
    )
    return knowledge


async def _order_context(user: User, order_id: str | None) -> str | None:
    if not order_id:
        return None
    order = await orders_repo.get_by_id(PydanticObjectId(order_id))
    if order is None or order.client_id != user.id:
        return None
    return f"El pedido {order.code} está en estado {order.status.value}."


async def chat(user: User, data: ChatRequest) -> ChatResponse:
    settings = get_settings()
    query_embedding = embeddings.embed(data.message)

    knowledge = await ai_repo.list_knowledge()
    by_id = {str(k.id): k for k in knowledge}
    ranked = retrieval.rank(
        query_embedding,
        [(str(k.id), k.embedding, k.content) for k in knowledge],
        top_k=settings.ai_top_k,
    )
    ranked = [r for r in ranked if r[1] > 0.0]  # drop unrelated

    sources = [
        SourceRef(
            id=kid,
            source_type=by_id[kid].source_type,
            snippet=content[:_SNIPPET_LEN],
        )
        for kid, _score, content in ranked
    ]
    contexts = [content for _kid, _score, content in ranked]

    order_ctx = await _order_context(user, data.order_id)
    if order_ctx is not None:
        contexts.insert(0, order_ctx)

    answer_text = await llm.answer(data.message, contexts)

    # persist the conversation (new or continued)
    conversation = None
    if data.conversation_id:
        conversation = await ai_repo.get_conversation(PydanticObjectId(data.conversation_id))
        if conversation is not None and conversation.user_id != user.id:
            raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)
    if conversation is None:
        conversation = AiConversation(user_id=user.id)
        await ai_repo.insert_conversation(conversation)

    conversation.messages.append(ConversationMessage(role="user", content=data.message))
    conversation.messages.append(ConversationMessage(role="assistant", content=answer_text))
    await conversation.save()

    return ChatResponse(answer=answer_text, conversation_id=str(conversation.id), sources=sources)


async def get_conversation(user: User, conversation_id: PydanticObjectId) -> AiConversation:
    conversation = await ai_repo.get_conversation(conversation_id)
    if conversation is None:
        raise AppError("Conversation not found", code="not_found", status_code=404)
    if conversation.user_id != user.id:
        raise AppError("Forbidden", code="forbidden", status_code=status.HTTP_403_FORBIDDEN)
    return conversation
