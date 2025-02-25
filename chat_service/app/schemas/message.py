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
