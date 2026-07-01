"""Data access for AI knowledge and conversations."""

from beanie import PydanticObjectId

from app.ai.models import AiConversation, AiKnowledge


async def insert_knowledge(knowledge: AiKnowledge) -> AiKnowledge:
    return await knowledge.insert()


async def list_knowledge(*, limit: int = 500) -> list[AiKnowledge]:
    # MVP: load the knowledge base and rank in-app. Replace with Atlas
    # $vectorSearch when the corpus grows.
    return await AiKnowledge.find_all().limit(limit).to_list()


async def insert_conversation(conversation: AiConversation) -> AiConversation:
    return await conversation.insert()


async def get_conversation(conversation_id: PydanticObjectId) -> AiConversation | None:
    return await AiConversation.get(conversation_id)
