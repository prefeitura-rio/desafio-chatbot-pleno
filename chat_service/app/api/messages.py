from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.message import (
    MessageCreate,
    MessageWithLLMParams,
    MessageResponse,
    MessageListResponse,
    SendMessageResponse,
    LLMParameters,
)
from app.models.message import Message
from app.services.chat_service import ChatService
from app.core.security import get_current_user

router = APIRouter(tags=["messages"])


@router.post(
    "/conversations/{conversation_id}/messages", response_model=SendMessageResponse
)
async def send_message(
    conversation_id: UUID,
    message: MessageWithLLMParams,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Send a message in a conversation.

    This endpoint adds a user message to the conversation and queues it for processing
    by the LLM service. The response is asynchronous, and the client should poll
    for the assistant's response.

    Args:
        conversation_id (UUID): Conversation ID
        message (MessageWithLLMParams): Message data with optional LLM parameters
        db (AsyncSession): Database session
        current_user (dict): Current authenticated user

    Returns:
        SendMessageResponse: Response containing the sent message and request ID
    """
    # Add user message to conversation
    user_message, request_id = await ChatService.add_user_message(
        db=db,
        conversation_id=conversation_id,
        user_id=UUID(current_user["id"]),
        message_data=MessageCreate(content=message.content),
        llm_params=message.llm_params,
    )

    return SendMessageResponse(
        message=MessageResponse.model_validate(user_message),
        request_id=UUID(request_id),
        status="processing",
    )


@router.get(
    "/conversations/{conversation_id}/messages", response_model=MessageListResponse
)
async def get_conversation_messages(
    conversation_id: UUID,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get messages for a conversation.

    Args:
        conversation_id (UUID): Conversation ID
        page (int): Page number
        page_size (int): Page size
        db (AsyncSession): Database session
        current_user (dict): Current authenticated user

    Returns:
        MessageListResponse: List of messages
    """
    messages, total = await ChatService.get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        user_id=UUID(current_user["id"]),
        page=page,
        page_size=page_size,
    )

    # Calculate total pages
    pages = (total + page_size - 1) // page_size

    return MessageListResponse(
        items=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        size=page_size,
        pages=pages,
    )


@router.get("/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get a message by ID.

    Args:
        message_id (UUID): Message ID
        db (AsyncSession): Database session
        current_user (dict): Current authenticated user

    Returns:
        MessageResponse: Message
    """
    # Get message from database
    message = await db.get(Message, message_id)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        )

    # Get conversation to check ownership
    conversation = await ChatService.get_conversation(
        db=db, conversation_id=message.conversation_id, user_id=UUID(current_user["id"])
    )

    return MessageResponse.model_validate(message)
