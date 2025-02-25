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


# schemas/message.py
"""
Pydantic models for Message-related requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field, validator


class MessageRole(str, Enum):
    """Enum for message roles matching the database model"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageBase(BaseModel):
    """Base Message model with shared attributes"""

    role: MessageRole = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Content of the message")


class MessageCreate(BaseModel):
    """Model for message creation request"""

    content: str = Field(..., description="Content of the user message")

    @validator("content")
    def content_not_empty(cls, v):
        """Validate that content is not empty"""
        if not v.strip():
            raise ValueError("Message content cannot be empty")
        return v


class LLMParameters(BaseModel):
    """Optional parameters for the LLM"""

    temperature: Optional[float] = Field(
        0.7, description="Temperature for generation", ge=0.0, le=2.0
    )
    max_tokens: Optional[int] = Field(
        None, description="Maximum number of tokens to generate"
    )
    top_p: Optional[float] = Field(
        1.0, description="Top p sampling parameter", gt=0.0, le=1.0
    )
    presence_penalty: Optional[float] = Field(
        0.0, description="Presence penalty", ge=-2.0, le=2.0
    )
    frequency_penalty: Optional[float] = Field(
        0.0, description="Frequency penalty", ge=-2.0, le=2.0
    )


class MessageWithLLMParams(MessageCreate):
    """Message creation with LLM parameters"""

    llm_params: Optional[LLMParameters] = Field(
        None, description="Parameters for the LLM"
    )


class MessageInDB(MessageBase):
    """Model for message data as stored in the database"""

    id: UUID = Field(..., description="Unique identifier")
    conversation_id: UUID = Field(
        ..., description="Conversation this message belongs to"
    )
    user_id: Optional[UUID] = Field(
        None, description="User who sent the message (if role is 'user')"
    )
    created_at: datetime = Field(..., description="When the message was created")

    # Optional fields for assistant messages
    model_used: Optional[str] = Field(None, description="Model used for generation")
    tokens_prompt: Optional[int] = Field(None, description="Number of prompt tokens")
    tokens_completion: Optional[int] = Field(
        None, description="Number of completion tokens"
    )
    processing_time: Optional[float] = Field(
        None, description="Processing time in seconds"
    )

    class Config:
        """Pydantic config"""

        from_attributes = True


class MessageResponse(MessageInDB):
    """Model for message response to clients"""

    pass


class MessageListResponse(BaseModel):
    """Model for paginated list of messages"""

    items: List[MessageResponse] = Field(..., description="List of messages")
    total: int = Field(..., description="Total number of messages")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")


class SendMessageResponse(BaseModel):
    """Response model when sending a new message"""

    message: MessageResponse = Field(..., description="The user message that was sent")
    request_id: UUID = Field(
        ..., description="ID to track the assistant's response processing"
    )
    status: str = Field(..., description="Status of the request")


# schemas/search.py
"""
Pydantic models for Semantic Search functionality.
"""

from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Model for search request"""

    query: str = Field(..., description="Text to search for")
    limit: Optional[int] = Field(
        10, description="Maximum number of results to return", gt=0, le=100
    )
    min_similarity: Optional[float] = Field(
        0.5, description="Minimum similarity threshold", ge=0.0, le=1.0
    )
    conversation_id: Optional[UUID] = Field(
        None, description="Limit search to a specific conversation"
    )


class SearchResultItem(BaseModel):
    """Model for a single search result item"""

    message_id: UUID = Field(..., description="ID of the message")
    conversation_id: UUID = Field(..., description="ID of the conversation")
    conversation_title: str = Field(..., description="Title of the conversation")
    content: str = Field(..., description="Content of the message")
    role: str = Field(..., description="Role of the message sender")
    created_at: datetime = Field(..., description="When the message was created")
    similarity: float = Field(..., description="Similarity score")


class SearchResponse(BaseModel):
    """Model for search response"""

    query: str = Field(..., description="Original search query")
    results: List[SearchResultItem] = Field(..., description="Search results")
