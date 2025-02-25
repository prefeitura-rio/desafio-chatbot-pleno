"""
Chat service implementation containing core business logic.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
)
from app.schemas.message import MessageCreate, MessageResponse, LLMParameters
from app.utils.cache import CacheService
from app.utils.queue import publish_message
from app.utils.embedding import get_text_embedding
from app.core.exceptions import ChatServiceException
from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize cache services
conversation_cache = CacheService[ConversationResponse](
    model_class=ConversationResponse, prefix="conversation", ttl=3600  # 1 hour
)

message_cache = CacheService[MessageResponse](
    model_class=MessageResponse, prefix="message", ttl=3600  # 1 hour
)


class ChatService:
    """
    Service for handling chat-related operations.

    This class implements the core business logic for conversations and messages,
    including conversation management, message processing, and interaction with
    the LLM service via the message queue.
    """

    @staticmethod
    async def create_conversation(
        db: AsyncSession, user_id: uuid.UUID, conversation_data: ConversationCreate
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            db (AsyncSession): Database session
            user_id (uuid.UUID): User ID
            conversation_data (ConversationCreate): Conversation data

        Returns:
            Conversation: Created conversation

        Raises:
            ChatServiceException: If conversation cannot be created
        """
        try:
            # Create conversation
            conversation = Conversation(
                user_id=user_id,
                title=conversation_data.title,
                system_prompt=conversation_data.system_prompt,
            )

            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)

            # If system prompt is provided, create system message
            if conversation_data.system_prompt:
                system_message = Message(
                    conversation_id=conversation.id,
                    role=MessageRole.SYSTEM,
                    content=conversation_data.system_prompt,
                )

                db.add(system_message)
                await db.commit()

            return conversation
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating conversation: {e}")
            raise ChatServiceException(
                status_code=500,
                detail="Failed to create conversation",
                code="conversation_creation_failed",
            )

    @staticmethod
    async def get_conversation(
        db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Conversation]:
        """
        Get conversation by ID.

        Args:
            db (AsyncSession): Database session
            conversation_id (uuid.UUID): Conversation ID
            user_id (uuid.UUID): User ID

        Returns:
            Optional[Conversation]: Conversation or None if not found

        Raises:
            ChatServiceException: If conversation not found or not owned by user
        """
        cached = await conversation_cache.get(str(conversation_id))
        if cached and cached.user_id == user_id:
            # Get fresh copy from database to include relationships
            conversation = await db.get(Conversation, conversation_id)
            if conversation:
                return conversation

        conversation = await db.get(Conversation, conversation_id)

        if not conversation:
            raise ChatServiceException(
                status_code=404,
                detail="Conversation not found",
                code="conversation_not_found",
            )

        if conversation.user_id != user_id:
            raise ChatServiceException(
                status_code=403,
                detail="Access denied to this conversation",
                code="access_denied",
            )

        await conversation_cache.set(
            str(conversation_id), ConversationResponse.model_validate(conversation)
        )

        return conversation

    @staticmethod
    async def list_conversations(
        db: AsyncSession, user_id: uuid.UUID, page: int = 1, page_size: int = 20
    ) -> Tuple[List[Conversation], int]:
        """
        List conversations for a user.

        Args:
            db (AsyncSession): Database session
            user_id (uuid.UUID): User ID
            page (int, optional): Page number. Defaults to 1.
            page_size (int, optional): Page size. Defaults to 20.

        Returns:
            Tuple[List[Conversation], int]: List of conversations and total count
        """
        # Count total conversations
        result = await db.execute(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.user_id == user_id)
        )
        total = result.scalar_one()

        # Get conversations for current page
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        conversations = result.scalars().all()

        return conversations, total

    @staticmethod
    async def update_conversation(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        conversation_data: ConversationUpdate,
    ) -> Conversation:
        """
        Update conversation.

        Args:
            db (AsyncSession): Database session
            conversation_id (uuid.UUID): Conversation ID
            user_id (uuid.UUID): User ID
            conversation_data (ConversationUpdate): Conversation data

        Returns:
            Conversation: Updated conversation

        Raises:
            ChatServiceException: If conversation not found or not owned by user
        """
        # Get conversation
        conversation = await ChatService.get_conversation(db, conversation_id, user_id)

        # Update fields if provided
        if conversation_data.title is not None:
            conversation.title = conversation_data.title

        if conversation_data.system_prompt is not None:
            conversation.system_prompt = conversation_data.system_prompt

            # Update or create system message
            result = await db.execute(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.role == MessageRole.SYSTEM,
                )
                .order_by(Message.created_at)
                .limit(1)
            )

            system_message = result.scalar_one_or_none()

            if system_message:
                system_message.content = conversation_data.system_prompt
            else:
                system_message = Message(
                    conversation_id=conversation_id,
                    role=MessageRole.SYSTEM,
                    content=conversation_data.system_prompt,
                )
                db.add(system_message)

        # Commit changes
        await db.commit()
        await db.refresh(conversation)

        # Invalidate cache
        await conversation_cache.delete(str(conversation_id))

        return conversation

    @staticmethod
    async def delete_conversation(
        db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """
        Delete conversation.

        Args:
            db (AsyncSession): Database session
            conversation_id (uuid.UUID): Conversation ID
            user_id (uuid.UUID): User ID

        Returns:
            bool: True if conversation was deleted

        Raises:
            ChatServiceException: If conversation not found or not owned by user
        """
        # Get conversation
        conversation = await ChatService.get_conversation(db, conversation_id, user_id)

        # Delete conversation (will cascade delete messages)
        await db.delete(conversation)
        await db.commit()

        # Invalidate cache
        await conversation_cache.delete(str(conversation_id))

        return True

    @staticmethod
    async def add_user_message(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        message_data: MessageCreate,
        llm_params: Optional[LLMParameters] = None,
    ) -> Tuple[Message, str]:
        """
        Add a user message to a conversation and queue it for processing.

        Args:
            db (AsyncSession): Database session
            conversation_id (uuid.UUID): Conversation ID
            user_id (uuid.UUID): User ID
            message_data (MessageCreate): Message data
            llm_params (Optional[LLMParameters]): LLM parameters

        Returns:
            Tuple[Message, str]: Created message and request ID

        Raises:
            ChatServiceException: If conversation not found or not owned by user
        """
        # Get conversation
        conversation = await ChatService.get_conversation(db, conversation_id, user_id)

        # Create message
        message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            role=MessageRole.USER,
            content=message_data.content,
        )

        # Create embedding
        embedding = await get_text_embedding(message_data.content)
        if embedding:
            message.embedding = embedding

        db.add(message)

        # Update conversation's updated_at timestamp
        conversation.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(message)

        # Prepare message for LLM service
        llm_message_data = {
            "message_id": str(message.id),
            "conversation_id": str(conversation_id),
            "user_id": str(user_id),
            "content": message_data.content,
        }

        # Add LLM parameters if provided
        if llm_params:
            llm_message_data["llm_params"] = llm_params.model_dump()

        # Queue message for processing
        request_id = await publish_message(llm_message_data)

        return message, request_id

    @staticmethod
    async def add_assistant_message(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        content: str,
        model_used: Optional[str] = None,
        tokens_prompt: Optional[int] = None,
        tokens_completion: Optional[int] = None,
        processing_time: Optional[float] = None,
    ) -> Message:
        """
        Add an assistant message to a conversation.

        Args:
            db (AsyncSession): Database session
            conversation_id (uuid.UUID): Conversation ID
            content (str): Message content
            model_used (Optional[str]): Model used for generation
            tokens_prompt (Optional[int]): Number of prompt tokens
            tokens_completion (Optional[int]): Number of completion tokens
            processing_time (Optional[float]): Processing time in seconds

        Returns:
            Message: Created message
        """
        # Create message
        message = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
            model_used=model_used,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            processing_time=processing_time,
        )

        # Create embedding
        embedding = await get_text_embedding(content)
        if embedding:
            message.embedding = embedding

        db.add(message)

        # Update conversation's updated_at timestamp
        conversation = await db.get(Conversation, conversation_id)
        if conversation:
            conversation.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(message)

        return message

    @staticmethod
    async def get_conversation_messages(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Message], int]:
        """
        Get messages for a conversation.

        Args:
            db (AsyncSession): Database session
            conversation_id (uuid.UUID): Conversation ID
            user_id (uuid.UUID): User ID
            page (int, optional): Page number. Defaults to 1.
            page_size (int, optional): Page size. Defaults to 50.

        Returns:
            Tuple[List[Message], int]: List of messages and total count

        Raises:
            ChatServiceException: If conversation not found or not owned by user
        """
        # Get conversation to check ownership
        await ChatService.get_conversation(db, conversation_id, user_id)

        # Count total messages
        result = await db.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        total = result.scalar_one()

        # Get messages for current page
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        messages = result.scalars().all()

        return messages, total

    @staticmethod
    async def get_conversation_history(
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history formatted for LLM context.

        Args:
            db (AsyncSession): Database session
            conversation_id (uuid.UUID): Conversation ID
            user_id (uuid.UUID): User ID
            limit (int, optional): Maximum number of messages. Defaults to 20.

        Returns:
            List[Dict[str, Any]]: Formatted message history for LLM

        Raises:
            ChatServiceException: If conversation not found or not owned by user
        """
        # Get conversation to check ownership
        conversation = await ChatService.get_conversation(db, conversation_id, user_id)

        # Get messages
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .limit(limit)
        )

        messages = result.scalars().all()

        # Format messages for LLM
        formatted_messages = []

        # Add system message if available
        if conversation.system_prompt:
            formatted_messages.append(
                {"role": "system", "content": conversation.system_prompt}
            )

        # Add rest of the messages
        for message in messages:
            # Only include user and assistant messages
            if message.role in [MessageRole.USER, MessageRole.ASSISTANT]:
                formatted_messages.append(
                    {"role": message.role.value, "content": message.content}
                )

        return formatted_messages

    @staticmethod
    async def perform_semantic_search(
        db: AsyncSession,
        user_id: uuid.UUID,
        query: str,
        conversation_id: Optional[uuid.UUID] = None,
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search on messages.

        Args:
            db (AsyncSession): Database session
            user_id (uuid.UUID): User ID
            query (str): Search query
            conversation_id (Optional[uuid.UUID]): Limit search to conversation. Defaults to None.
            limit (int, optional): Maximum number of results. Defaults to 10.
            min_similarity (float, optional): Minimum similarity threshold. Defaults to 0.5.

        Returns:
            List[Dict[str, Any]]: Search results
        """
        # Get query embedding
        query_embedding = await get_text_embedding(query)
        if not query_embedding:
            raise ChatServiceException(
                status_code=500,
                detail="Failed to generate embedding for search query",
                code="embedding_generation_failed",
            )

        # Build SQL query
        # This uses the pgvector extension's cosine similarity operator (<=>)
        sql_query = """
        SELECT 
            m.id, 
            m.content, 
            m.role, 
            m.created_at,
            m.conversation_id,
            c.title as conversation_title,
            1 - (m.embedding <=> :query_embedding) as similarity
        FROM 
            messages m
        JOIN 
            conversations c ON m.conversation_id = c.id
        WHERE 
            c.user_id = :user_id
            AND 1 - (m.embedding <=> :query_embedding) >= :min_similarity
        """

        # Add conversation filter if provided
        params = {
            "query_embedding": query_embedding,
            "user_id": user_id,
            "min_similarity": min_similarity,
        }

        if conversation_id:
            sql_query += " AND m.conversation_id = :conversation_id"
            params["conversation_id"] = conversation_id

        # Add ordering and limit
        sql_query += """
        ORDER BY 
            similarity DESC
        LIMIT 
            :limit
        """
        params["limit"] = limit

        # Execute query
        result = await db.execute(sql_query, params)
        rows = result.fetchall()

        # Format results
        results = []
        for row in rows:
            results.append(
                {
                    "message_id": row.id,
                    "content": row.content,
                    "role": row.role,
                    "created_at": row.created_at,
                    "conversation_id": row.conversation_id,
                    "conversation_title": row.conversation_title,
                    "similarity": row.similarity,
                }
            )

        return results


# services/embedding_service.py
"""
Service for handling text embeddings.
"""

import logging
from typing import List, Optional
import httpx

from app.core.config import settings
from app.core.exceptions import ChatServiceException

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings.

    This service provides methods to generate vector embeddings
    for text using OpenAI's API or other embedding models.
    """

    @staticmethod
    async def get_embedding(text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using OpenAI's embedding model.

        Args:
            text (str): Text to embed

        Returns:
            Optional[List[float]]: Vector embedding or None if error

        Raises:
            ChatServiceException: If embedding generation fails
        """
        # Ensure text is not empty
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None

        try:
            # Truncate text if too long
            # OpenAI's embedding models have a token limit
            if len(text) > 8000:
                text = text[:8000]

            # Use httpx for API request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={"input": text, "model": settings.EMBEDDING_MODEL},
                )

                # Check for errors
                if response.status_code != 200:
                    logger.error(f"OpenAI API error: {response.text}")
                    raise ChatServiceException(
                        status_code=500,
                        detail="Failed to generate embedding",
                        code="embedding_generation_failed",
                    )

                # Parse response
                data = response.json()

                # Extract embedding
                embedding = data["data"][0]["embedding"]

                return embedding
        except httpx.RequestError as e:
            logger.error(f"Error connecting to OpenAI API: {e}")
            raise ChatServiceException(
                status_code=500,
                detail="Failed to connect to embedding service",
                code="embedding_service_connection_failed",
            )
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise ChatServiceException(
                status_code=500,
                detail="Unknown error generating embedding",
                code="embedding_generation_error",
            )
