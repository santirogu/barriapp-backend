"""AI assistant endpoints. See docs/API_CONTRACT.md §13 and docs/ARCHITECTURE.md §3."""

from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, status

from app.ai import service
from app.ai.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationPublic,
    KnowledgeIngest,
    KnowledgePublic,
)
from app.core.deps import CurrentUser, require_roles
from app.core.ratelimit import rate_limiter
from app.users.models import Role, User

router = APIRouter(prefix="/ai", tags=["ai"])

AdminUser = Annotated[User, Depends(require_roles(Role.SUPER_ADMIN))]


@router.post("/knowledge", response_model=KnowledgePublic, status_code=status.HTTP_201_CREATED)
async def ingest_knowledge(data: KnowledgeIngest, admin: AdminUser) -> KnowledgePublic:
    return KnowledgePublic.from_knowledge(await service.ingest_knowledge(admin, data))


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(rate_limiter("ai_chat"))])
async def chat(data: ChatRequest, user: CurrentUser) -> ChatResponse:
    return await service.chat(user, data)


@router.get("/conversations/{conversation_id}", response_model=ConversationPublic)
async def get_conversation(
    conversation_id: PydanticObjectId, user: CurrentUser
) -> ConversationPublic:
    return ConversationPublic.from_conversation(
        await service.get_conversation(user, conversation_id)
    )
