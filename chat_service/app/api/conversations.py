# api/conversations.py
"""
API routes for conversation management.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
)
from app.services.chat_service import ChatService
from app.core.security import get_current_user

router = APIRouter(tags=["conversations"])


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    conversation: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Create a new conversation.

    Args:
        conversation (ConversationCreate): Conversation data
        db (AsyncSession): Database session
        current_user (dict): Current authenticated user

    Returns:
        ConversationResponse: Created conversation
    """
    conversation_obj = await ChatService.create_conversation(
        db=db, user_id=UUID(current_user["id"]), conversation_data=conversation
    )

    return ConversationResponse.model_validate(conversation_obj)


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    List conversations for the current user.

    Args:
        page (int): Page number
        page_size (int): Page size
        db (AsyncSession): Database session
        current_user (dict): Current authenticated user

    Returns:
        ConversationListResponse: List of conversations
    """
    conversations, total = await ChatService.list_conversations(
        db=db, user_id=UUID(current_user["id"]), page=page, page_size=page_size
    )

    # Calculate total pages
    pages = (total + page_size - 1) // page_size

    return ConversationListResponse(
        items=[ConversationResponse.model_validate(c) for c in conversations],
        total=total,
        page=page,
        size=page_size,
        pages=pages,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get a conversation by ID.

    Args:
        conversation_id (UUID): Conversation ID
        db (AsyncSession): Database session
        current_user (dict): Current authenticated user

    Returns:
        ConversationResponse: Conversation
    """
    conversation = await ChatService.get_conversation(
        db=db, conversation_id=conversation_id, user_id=UUID(current_user["id"])
    )

    return ConversationResponse.model_validate(conversation)


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    conversation: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Update a conversation.

    Args:
        conversation_id (UUID): Conversation ID
        conversation (ConversationUpdate): Updated conversation data
        db (AsyncSession): Database session
        current_user (dict): Current authenticated user

    Returns:
        ConversationResponse: Updated conversation
    """
    updated_conversation = await ChatService.update_conversation(
        db=db,
        conversation_id=conversation_id,
        user_id=UUID(current_user["id"]),
        conversation_data=conversation,
    )

    return ConversationResponse.model_validate(updated_conversation)


@router.delete(
    "/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Delete a conversation.

    Args:
        conversation_id (UUID): Conversation ID
        db (AsyncSession): Database session
        current_user (dict): Current authenticated user
    """
    await ChatService.delete_conversation(
        db=db, conversation_id=conversation_id, user_id=UUID(current_user["id"])
    )

    return None
