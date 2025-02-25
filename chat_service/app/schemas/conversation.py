"""
Pydantic models for Conversation-related requests and responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field


class ConversationBase(BaseModel):
    """Base Conversation model with shared attributes"""

    title: str = Field(..., description="Title of the conversation")
    system_prompt: Optional[str] = Field(
        None, description="System prompt to initialize conversation context"
    )


class ConversationCreate(ConversationBase):
    """Model for conversation creation request"""

    pass


class ConversationUpdate(BaseModel):
    """Model for conversation update request"""

    title: Optional[str] = Field(None, description="New title for the conversation")
    system_prompt: Optional[str] = Field(None, description="Updated system prompt")


class ConversationInDB(ConversationBase):
    """Model for conversation data as stored in the database"""

    id: UUID = Field(..., description="Unique identifier")
    user_id: UUID = Field(..., description="User who owns this conversation")
    created_at: datetime = Field(..., description="When the conversation was created")
    updated_at: datetime = Field(
        ..., description="When the conversation was last updated"
    )

    class Config:
        """Pydantic config"""

        from_attributes = True


class ConversationResponse(ConversationInDB):
    """Model for conversation response to clients"""

    message_count: Optional[int] = Field(
        None, description="Total number of messages in the conversation"
    )
    last_message_at: Optional[datetime] = Field(
        None, description="Timestamp of the last message"
    )


class ConversationListResponse(BaseModel):
    """Model for paginated list of conversations"""

    items: List[ConversationResponse] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
